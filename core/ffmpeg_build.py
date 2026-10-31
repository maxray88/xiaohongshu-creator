#!/usr/bin/env python3
"""视频合成 —— Qwen3-TTS VoiceDesign 调用、ffmpeg 分段、拼接、清理。

从 _cron_assemble.py 拆出（S1）。2026-10-12：generate_tts 由「云端 TTS 子进程」
换成 Qwen3-TTS VoiceDesign 本地内存调用（原因：原云端服务上游返回 403），
其余函数未改。
"""
import hashlib, importlib.util, os, subprocess, sys, time


# ── Qwen3-TTS VoiceDesign 参数（全卡统一音色） ──
QWEN_TTS_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
QWEN_TTS_INSTRUCT = "一位温柔的成年女性，声音轻柔细腻、气息平稳，语速比日常稍快一点，适合情感树洞类的治愈系口播。"
QWEN_TTS_SPEED = 1.1
QWEN_TTS_LANG = "zh"

# ── 整段生成再切分参数（spec 3.7） ──
CARD_GAP_SECONDS = 0.5          # 用户指定：卡间停顿 0.5s
SILENCE_THRESHOLD_DB = -40      # 探针实测有效值
SILENCE_MIN_DURATION = 0.25     # 探针实测有效值
SNAP_MAX_DEVIATION = 2.0        # 超过则不吸附，用预估值


def _detect_silence(audio_path):
    """Detect silence intervals using ffmpeg silencedetect.

    Returns a list of (start, end) tuples (seconds).
    """
    r = subprocess.run(
        ["ffmpeg", "-i", audio_path,
         "-af", f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:d={SILENCE_MIN_DURATION}",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    intervals = []
    start = None
    for line in r.stderr.split("\n"):
        if "silence_start" in line:
            try:
                start = float(line.split("silence_start:")[1].strip())
            except (ValueError, IndexError):
                pass
        elif "silence_end" in line and start is not None:
            try:
                end = float(line.split("silence_end:")[1].split("|")[0].strip())
                intervals.append((start, end))
            except (ValueError, IndexError):
                pass
            start = None
    return intervals


def _snap_to_silence(estimated, silence_intervals):
    """Find the nearest silence midpoint to the estimated split point.

    Returns (snapped_point, deviation, used_estimate).
    If no silence is within SNAP_MAX_DEVIATION, returns the estimated point.
    """
    if not silence_intervals:
        return estimated, 0.0, True
    best_mid = None
    best_dev = float("inf")
    for s, e in silence_intervals:
        mid = (s + e) / 2
        dev = abs(mid - estimated)
        if dev < best_dev:
            best_dev = dev
            best_mid = mid
    if best_dev > SNAP_MAX_DEVIATION:
        return estimated, best_dev, True
    return best_mid, best_dev, False


def get_audio_duration(audio_path):
    """Get duration of an audio file in seconds using ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _valid_mp4(path, expected_duration):
    """True if `path` is a readable MP4 whose duration roughly matches expected."""
    if not os.path.isfile(path) or os.path.getsize(path) < 1024:
        return False
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    try:
        actual = float(r.stdout.strip())
    except ValueError:
        return False
    return actual > 0.5 and abs(actual - expected_duration) <= 3.0


def generate_tts(texts, video_dir):
    """
    Generate TTS for all cards using Qwen3-TTS VoiceDesign.

    B方案（整段生成再切分）：把 6 段文案用 。 连接成整段 → 一次
    generate_audio 调用 → 按字符比例预估切点 → 吸附最近静音中点 →
    ffmpeg 切分 → 每张卡首尾各补 0.25s 静音 → ffprobe 量最终时长。

    缓存：6 个 card_{i}.txt 指纹 + 1 个 joined.txt 整段指纹。
    全部有效才复用；任意一张失效 → 整段重新生成，全部重写指纹。

    Returns (durations_dict, engine_name).
    """
    durations = {}
    if importlib.util.find_spec("mlx_audio") is None:
        print("[FATAL] mlx_audio not found. Install with: "
              f"{sys.executable} -m pip install mlx mlx-audio")
        sys.exit(1)

    if not QWEN_TTS_INSTRUCT.strip():
        print("[FATAL] Qwen3-TTS VoiceDesign 的 instruct 音色描述不能为空"
              "（QWEN_TTS_INSTRUCT 为空 → 合成时抛 ValueError）。")
        sys.exit(1)

    print(f"\n[STEP 3] Generating TTS audio (Qwen3-TTS VoiceDesign, {QWEN_TTS_MODEL}, "
          f"speed {QWEN_TTS_SPEED}x, lang {QWEN_TTS_LANG})...")

    # ── Step 1: 构建整段文本与各卡指纹 ──
    card_texts = {}  # i -> 去尾部 。 的文本
    for i in sorted(texts.keys()):
        text = texts.get(i, "").strip()
        if not text:
            durations[i] = 0.0
            continue
        card_texts[i] = text.rstrip("。").rstrip()

    if len(card_texts) < 6:
        print(f"[FATAL] Only {len(card_texts)}/6 cards have non-empty text")
        sys.exit(1)

    sorted_indices = sorted(card_texts.keys())

    # 整段文本：text1。text2。...。text6。
    # cumulative_chars[k] = 前 k 张卡的累计字符数（含每段末尾补的 。）
    joined_parts = []
    cumulative_chars = [0]
    total_chars = 0
    for i in sorted_indices:
        part = card_texts[i] + "。"
        joined_parts.append(part)
        total_chars += len(part)
        cumulative_chars.append(total_chars)

    joined_text = "".join(joined_parts)
    joined_hash = hashlib.sha1(joined_text.encode("utf-8")).hexdigest()[:12]
    joined_hash_path = os.path.join(video_dir, "joined.txt")

    # ── Step 2: 缓存检查 — 6 张卡 + joined.txt 全部有效才复用 ──
    all_cached = True
    for i in sorted_indices:
        text = texts.get(i, "").strip()
        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        hash_path = os.path.join(video_dir, f"card_{i}.txt")
        wav_path = os.path.join(video_dir, f"card_{i}.wav")
        cached_ok = (
            os.path.isfile(wav_path) and os.path.getsize(wav_path) > 1000
            and os.path.isfile(hash_path)
            and open(hash_path, encoding="utf-8").read().strip() == text_hash
        )
        if not cached_ok:
            all_cached = False
            break

    joined_cached = (
        os.path.isfile(joined_hash_path)
        and open(joined_hash_path, encoding="utf-8").read().strip() == joined_hash
    )

    if all_cached and joined_cached:
        print("  [CACHE] All 6 card fingerprints + joined.txt valid — reusing cached WAVs")
        cache_valid = True
        for i in sorted_indices:
            wav_path = os.path.join(video_dir, f"card_{i}.wav")
            dur = get_audio_duration(wav_path)
            if dur > 0.5:
                durations[i] = dur
            else:
                print(f"  [WARN] card_{i}.wav duration too short ({dur:.2f}s) — cache invalid")
                cache_valid = False
                break
        if cache_valid:
            return durations, "qwen3-tts-voicedesign"
        all_cached = False

    # ── Step 3: 整段生成（模型只加载一次） ──
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model

    t_load = time.time()
    print(f"  [MODEL] loading {QWEN_TTS_MODEL} (once, shared by all cards)...")
    model = load_model(QWEN_TTS_MODEL)
    print(f"  [MODEL] loaded in {time.time() - t_load:.1f}s")

    t1 = time.time()
    joined_wav_path = os.path.join(video_dir, "joined.wav")

    last_error = ""
    ok = False
    for attempt in range(3):
        file_prefix = f"joined_tts{attempt}"
        before_wavs = {f for f in os.listdir(video_dir) if f.endswith(".wav")}
        try:
            generate_audio(
                text=joined_text, model=model, instruct=QWEN_TTS_INSTRUCT,
                speed=QWEN_TTS_SPEED, lang_code=QWEN_TTS_LANG,
                max_tokens=4096, output_path=video_dir,
                file_prefix=file_prefix, audio_format="wav", verbose=False,
            )
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"[-300:]
        else:
            new_wavs = sorted(f for f in os.listdir(video_dir)
                              if f.endswith(".wav") and f not in before_wavs)
            if len(new_wavs) != 1:
                last_error = "expected exactly 1 new .wav, got %d" % len(new_wavs)
                if new_wavs:
                    last_error += ": %s" % new_wavs[:3]
            elif os.path.getsize(os.path.join(video_dir, new_wavs[0])) <= 1000:
                last_error = "produced wav suspiciously small (<=1000 bytes)"
            else:
                os.replace(os.path.join(video_dir, new_wavs[0]), joined_wav_path)
                ok = True
        if ok:
            break
        if attempt < 2:
            print(f"  ⚠️  retry {attempt + 1}/3 for joined TTS...")
            time.sleep(5)

    if not ok:
        print(f"  [FATAL] Joined TTS generation failed (3 attempts)")
        if last_error:
            print(f"     last error: {last_error}")
        sys.exit(1)

    print(f"  [TTS] Joined audio generated in {time.time() - t1:.1f}s")

    # ── Step 4: 静音检测与切点计算 ──
    total_dur = get_audio_duration(joined_wav_path)
    print(f"  [SPLIT] Joined audio duration: {total_dur:.2f}s")

    silence_intervals = _detect_silence(joined_wav_path)
    print(f"  [SPLIT] Found {len(silence_intervals)} silence intervals")

    # 预估切点：total_dur * (累计字符数 / 总字符数)
    split_points = []
    for idx_pos in range(len(sorted_indices) - 1):
        cumulative = cumulative_chars[idx_pos + 1]
        est = total_dur * (cumulative / total_chars)
        split_points.append(est)

    # 吸附最近静音中点
    snapped_points = []
    for sp_idx, est in enumerate(split_points):
        snapped, deviation, used_est = _snap_to_silence(est, silence_intervals)
        if used_est:
            print(f"  ⚠️  Split point {sp_idx + 1}: estimated {est:.2f}s, "
                  f"nearest silence deviates {deviation:.2f}s (> {SNAP_MAX_DEVIATION}s) — using estimate")
        else:
            print(f"  [SPLIT] Point {sp_idx + 1}: estimated {est:.2f}s → snapped to {snapped:.2f}s "
                  f"(deviation {deviation:.2f}s)")
        snapped_points.append(snapped)

    # 最后一张卡的切点固定为音频总时长，不吸附
    snapped_points.append(total_dur)

    # 切点必须严格递增
    for j in range(1, len(snapped_points)):
        if snapped_points[j] <= snapped_points[j - 1]:
            print(f"  [FATAL] Split points not strictly increasing: "
                  f"{snapped_points[j - 1]:.2f} >= {snapped_points[j]:.2f}")
            sys.exit(1)

    # ── Step 5: 切分 → 补静音 → ffprobe 量最终时长 ──
    bounds = [0.0] + snapped_points
    for idx_pos, i in enumerate(sorted_indices):
        start = bounds[idx_pos]
        end = bounds[idx_pos + 1]

        temp_split = os.path.join(video_dir, f"_split_{i}.wav")

        # 切分
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
             "-i", joined_wav_path, "-c", "copy", temp_split],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0 or not os.path.isfile(temp_split):
            print(f"  [FATAL] Split card_{i} failed: {r.stderr[-300:]}")
            sys.exit(1)

        # 每张卡首尾各补 0.25s 静音
        wav_path = os.path.join(video_dir, f"card_{i}.wav")
        half_gap_ms = int(CARD_GAP_SECONDS * 500)
        half_gap_s = CARD_GAP_SECONDS / 2
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", temp_split,
             "-af", f"adelay={half_gap_ms}:all=1,apad=pad_dur={half_gap_s}",
             wav_path],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0 or not os.path.isfile(wav_path):
            print(f"  [FATAL] Pad card_{i} failed: {r.stderr[-300:]}")
            sys.exit(1)

        os.remove(temp_split)

        # ⭐ 补完静音后再量时长（spec 3.4）
        dur = get_audio_duration(wav_path)
        durations[i] = dur

        # 写单卡指纹
        text = texts.get(i, "").strip()
        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        hash_path = os.path.join(video_dir, f"card_{i}.txt")
        try:
            with open(hash_path, "w", encoding="utf-8") as f:
                f.write(text_hash)
        except OSError as e:
            print(f"     (无法写指纹文件，下次将重新生成: {e})")

        print(f"  ✅ card_{i}.wav ({dur:.2f}s, split {start:.2f}–{end:.2f}s)")

    # 写整段指纹
    try:
        with open(joined_hash_path, "w", encoding="utf-8") as f:
            f.write(joined_hash)
    except OSError as e:
        print(f"     (无法写 joined.txt 指纹文件: {e})")

    # 清理整段临时文件
    if os.path.isfile(joined_wav_path):
        os.remove(joined_wav_path)

    # Validate: need at least 6 cards with valid TTS duration
    valid = {k: v for k, v in durations.items() if v > 0.5}
    if len(valid) < 6:
        failed_cards = [k for k in sorted(durations.keys()) if durations.get(k, 0) <= 0.5]
        print(f"[FATAL] Only {len(valid)}/6 valid TTS files. Failed cards: {failed_cards}")
        sys.exit(1)

    return durations, "qwen3-tts-voicedesign"


def build_segments(manifest, images_dir, video_dir, durations):
    """Build and concatenate video segments."""
    print("\n[STEP 4] Building video segments...")
    segments = []
    card_types = {}
    for card in manifest.get("cards", []):
        i = card["index"]
        img_file = card["file"]
        img_path = os.path.join(images_dir, img_file)
        if not os.path.isfile(img_path):
            print(f"  [ERROR] Image not found: {img_path}")
            continue
        dur = durations.get(i, 3.0)
        padded_path = os.path.join(video_dir, f"pad_{i}.png")
        seg_path = os.path.join(video_dir, f"seg_{i}.mp4")
        audio_path = os.path.join(video_dir, f"card_{i}.wav")

        r = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", img_path
        ], capture_output=True, text=True)
        if r.returncode != 0:
            # manifest 指向了非图片（如 .html 残留，day70 事故）：ffprobe 直接失败。
            # 在此大声拦截，而不是让下游 pad/seg 报 6 条难懂的错。
            print(f"  [ERROR] Not a readable image: {img_path} "
                  f"(manifest file 字段疑似未翻转 .html→.jpg)")
            continue
        dims = r.stdout.strip().split(",")
        ow, oh = (int(dims[0]), int(dims[1])) if len(dims) == 2 else (1080, 1440)
        ctype = card.get("type", f"card{i}")
        card_types[i] = ctype
        print(f"  card_{i} ({ctype}): {ow}×{oh}, TTS {dur:.2f}s")

        # Pad to 1080×1920
        r = subprocess.run([
            "ffmpeg", "-y", "-i", img_path,
            "-vf", "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#1A1A2E",
            "-frames:v", "1", padded_path
        ], capture_output=True, text=True, timeout=30)
        if r.returncode != 0 or not os.path.isfile(padded_path):
            print(f"  [ERROR] pad {i} failed: {r.stderr[-200:]}")
            continue

        # Video segment — try Hyperframes (Ken Burns + safe margin) first, then ffmpeg
        # Hyperframes adds gentle motion to static cards; ffmpeg is the proven still-image fallback.
        hf_ok = False
        try:
            hf_ok = render_segment(padded_path, dur, seg_path)
            if hf_ok:
                print(f"  [OK] seg_{i}.mp4 ({dur:.2f}s) via Hyperframes")
                segments.append(seg_path)
                continue
        except Exception:
            hf_ok = False

        r = subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", padded_path, "-i", audio_path,
            "-c:v", "libx264", "-preset", "veryfast", "-t", f"{dur:.3f}", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", seg_path
        ], capture_output=True, text=True, timeout=120)

        if r.returncode != 0:
            print(f"  [ERROR] seg {i} failed: {r.stderr[-200:]}")
            continue
        segments.append(seg_path)
        print(f"  [OK] seg_{i}.mp4 ({dur:.2f}s)")

    if len(segments) < 6:
        print(f"[FATAL] Only {len(segments)} segments, need 6")
        sys.exit(1)
    return segments, card_types


def concat_segments(segments, video_dir, expected_duration):
    """Concat demuxer.

    All segments are encoded identically by build_segments, so a stream-copy
    concat is near-instant and lossless; fall back to a fast re-encode if the
    copy output is invalid (the proven uploadable format).
    """
    print("\n[STEP 5] Concatenating segments...")
    list_file = os.path.join(video_dir, "video_list.txt")
    with open(list_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    output_path = os.path.join(video_dir, "video_note.mp4")

    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c", "copy", "-movflags", "+faststart", output_path
    ], capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and _valid_mp4(output_path, expected_duration):
        print("  [OK] concatenated via stream copy (lossless, fast)")
    else:
        print("  stream copy produced invalid output — re-encoding (veryfast)")
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output_path
        ], capture_output=True, text=True, timeout=300)
        # 重编码后必须同样校验：returncode==0 不代表产物可用
        # （day70 事故的教训：ffmpeg 静默产出损坏文件，一路带到发布才炸）。
        if r.returncode == 0 and not _valid_mp4(output_path, expected_duration):
            got = get_audio_duration(output_path)
            print(f"  [ERROR] re-encode exited 0 but output is invalid "
                  f"(expected ≈{expected_duration:.1f}s, got {got:.1f}s)")
            sys.exit(1)
    if r.returncode != 0:
        print(f"[ERROR] Concat failed: {r.stderr[-500:]}")
        sys.exit(1)

    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration,size",
        "-of", "csv=p=0", output_path
    ], capture_output=True, text=True)
    finfo = r.stdout.strip().split(",")
    # ffprobe 对某些容器返回 "N/A" —— 直接 float() 会崩，
    # 而这里崩掉等于丢掉已经生成好的视频
    try:
        final_duration = float(finfo[0]) if len(finfo) > 0 else 0.0
    except (ValueError, IndexError):
        final_duration = 0.0
    try:
        final_size = int(float(finfo[1])) if len(finfo) > 1 else 0
    except (ValueError, IndexError):
        final_size = 0
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", output_path
    ], capture_output=True, text=True)
    vdims = r.stdout.strip().split(",")
    vw, vh = vdims if len(vdims) == 2 else ("1080", "1920")
    return output_path, final_duration, final_size, vw, vh


def cleanup(video_dir):
    """Remove temp files."""
    print("\n[STEP 6] Cleaning up...")
    cleaned = 0
    for i in range(1, 7):
        for fname in [f"pad_{i}.png", f"seg_{i}.mp4"]:
            fp = os.path.join(video_dir, fname)
            if os.path.isfile(fp):
                os.remove(fp)
                cleaned += 1
    for fname in ["video_list.txt", "_tts_config.json", "joined.wav"]:
        fp = os.path.join(video_dir, fname)
        if os.path.isfile(fp):
            os.remove(fp)
            cleaned += 1
    for i in range(1, 7):
        fp = os.path.join(video_dir, f"_split_{i}.wav")
        if os.path.isfile(fp):
            os.remove(fp)
            cleaned += 1
    print(f"  Removed {cleaned} temp files. Keeping: video_note.mp4 + card_*.wav + card_*.txt + joined.txt")


def hyperframes_available() -> bool:
    """hyperframes CLI 是否可用。"""
    return subprocess.run(["which", "hyperframes"], capture_output=True).returncode == 0


def render_segment(image: str, duration: float, out: str, safe_margin: int = 48) -> bool:
    """用 Hyperframes 渲染一段带 Ken Burns 动效的片段。

    返回 True 表示成功；返回 False 表示**调用方**应回落到 ffmpeg
    静帧方案（回落逻辑在 build_segments，不在此函数内）。
    """
    if not hyperframes_available():
        return False
    try:
        # Hyperframes example: hyperframes zoom --input card.jpg --duration 6.9 --out seg.mp4
        # Actual flags depend on installed version; keep minimal and catch failures.
        cmd = ["hyperframes", "zoom", "--input", image, "--duration", str(duration), "--output", out, "--margin", str(safe_margin)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and os.path.isfile(out)
    except Exception as e:
        print(f"[DBG] hyperframes render failed: {e}", file=sys.stderr)
        return False
