#!/usr/bin/env python3
"""视频合成 —— Edge-TTS 调用、ffmpeg 分段、拼接、清理。

从 _cron_assemble.py 拆出（S1）。函数体逐字未改。
"""
import hashlib, os, subprocess, sys, time


# ── Edge-TTS 参数（确定性发音，全卡同一声音） ──
TTS_VOICE = "zh-CN-XiaoyiNeural"
TTS_RATE = "+10%"


def get_audio_duration(mp3_path):
    """Get duration of MP3 in seconds using ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3_path],
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
    Generate TTS for all cards using Edge-TTS (统一声音).
    Skips cards that already have valid cached MP3s.
    Returns (durations_dict, engine_name).
    """
    durations = {}
    edge_ok = subprocess.run(["which", "edge-tts"], capture_output=True).returncode == 0
    if not edge_ok:
        print("[FATAL] edge-tts not found. Install with: pip install edge-tts")
        sys.exit(1)

    print(f"\n[STEP 3] Generating TTS audio (Edge-TTS, {TTS_VOICE}, {TTS_RATE})...")

    for i in sorted(texts.keys()):
        text = texts.get(i, "").strip()
        last_error = ""   # 首次就失败时也要能报出原因
        if not text:
            durations[i] = 0.0
            continue

        mp3_path = os.path.join(video_dir, f"card_{i}.mp3")

        # Cache check — reuse if valid.
        #
        # 关键：缓存有效性必须绑定**文本内容**，不只是「文件存在且 >1000 字节」。
        # 旧实现只看文件大小，于是改了文案（01:30 去AI味、或 04:00 重跑
        # 修好切片 bug）之后，卡2/卡3 仍复用旧音频 —— 视频里的声音
        # 和卡片文字对不上，而且没有任何提示。2026-09-27 day82 就是这样：
        # 修好「两卡念同一段」后重跑 04:00，必须手动删 mp3 才能生效。
        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        hash_path = os.path.join(video_dir, f"card_{i}.txt")
        cached_ok = (
            os.path.isfile(mp3_path) and os.path.getsize(mp3_path) > 1000
            and os.path.isfile(hash_path)
            and open(hash_path, encoding="utf-8").read().strip() == text_hash
        )
        if cached_ok:
            dur = get_audio_duration(mp3_path)
            if dur > 0.5:
                print(f"  [CACHE] card_{i}.mp3 ({dur:.2f}s)")
                durations[i] = dur
                continue
        elif os.path.isfile(mp3_path) and os.path.getsize(mp3_path) > 1000:
            print(f"  ♻️  card_{i}.mp3 缓存已过期（文案变了）—— 重新生成")

        t1 = time.time()
        # Retry transient failures (DNS, network glitches)
        last_error = ""
        for attempt in range(3):
            r = subprocess.run(
                ["edge-tts", "--voice", TTS_VOICE, "--rate", TTS_RATE,
                 "--text", text, "--write-media", mp3_path],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0 and os.path.isfile(mp3_path) and os.path.getsize(mp3_path) > 1000:
                break
            # 记下最后一次失败原因：旧代码赋值却从不使用，
            # 于是重试 3 次全失败后只报一句「failed (exit N)」，
            # 看不到 stderr 里的真实原因（DNS? 配额? 声音名不对?）。
            last_error = r.stderr.strip()[-300:]
            if attempt < 2:
                print(f"  ⚠️  retry {attempt + 1}/3 for card_{i}...")
                time.sleep(5)
        wall = time.time() - t1

        if r.returncode == 0 and os.path.isfile(mp3_path) and os.path.getsize(mp3_path) > 1000:
            dur = get_audio_duration(mp3_path)
            durations[i] = round(dur, 1)
            # 记录文本指纹，供下次运行判断缓存是否过期
            try:
                with open(hash_path, "w", encoding="utf-8") as f:
                    f.write(text_hash)
            except OSError as e:
                print(f"     (无法写指纹文件，下次将重新生成: {e})")
            print(f"  ✅ card_{i}.mp3 ({dur:.1f}s, {wall:.1f}s wall)")
        else:
            print(f"  ⚠️  card_{i}.mp3 failed (exit {r.returncode})")
            if r.stderr:
                print(f"     stderr: {r.stderr.strip()[-300:]}")
            if last_error and last_error != r.stderr.strip()[-300:]:
                print(f"     last retry error: {last_error}")
            durations[i] = 0.0

    # Validate: need at least 6 cards with valid TTS duration
    valid = {k: v for k, v in durations.items() if v > 0.5}
    if len(valid) < 6:
        failed_cards = [k for k in sorted(durations.keys()) if durations.get(k, 0) <= 0.5]
        print(f"[FATAL] Only {len(valid)}/6 valid TTS files. Failed cards: {failed_cards}")
        sys.exit(1)

    return durations, "edge-tts"


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
        mp3_path = os.path.join(video_dir, f"card_{i}.mp3")

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
            "ffmpeg", "-y", "-loop", "1", "-i", padded_path, "-i", mp3_path,
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
    for fname in ["video_list.txt", "_tts_config.json"]:
        fp = os.path.join(video_dir, fname)
        if os.path.isfile(fp):
            os.remove(fp)
            cleaned += 1
    print(f"  Removed {cleaned} temp files. Keeping: video_note.mp4 + card_*.mp3 + card_*.txt")


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
