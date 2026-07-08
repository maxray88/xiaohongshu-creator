#!/usr/bin/env python3
"""
HyperFrames HTML-to-MP4 Renderer for Xiaohongshu Videos
=========================================================

Generates animated video posts from HTML compositions using HyperFrames.
Integrates with the existing xhs_image_pipeline cover system.

Usage:
    # Render a simple animated title card
    $PYTHON xhs_hyperframes_video.py \
        --title "美伢的5个真相" \
        --subtitle "看完妈妈们都哭了" \
        --emoji "😭" \
        --cta "你家娃也这样吗？" \
        --bg /path/to/background.jpg \
        --output /tmp/xhs_video.mp4

    # Render with key points (animated entrance)
    $PYTHON xhs_hyperframes_video.py \
        --title "美伢的5个真相" \
        --key-points "葱油拌面·香到邻居" "番茄鸡蛋面·酸甜开胃" "麻酱拌面·灵魂拌一拌" \
        --kp-emojis "🧅" "🍅" "🥜" \
        --bg /path/to/background.jpg \
        --output /tmp/xhs_video.mp4

Requirements:
    - HyperFrames CLI (npx hyperframes)
    - FFmpeg in PATH
    - Chrome/Chromium installed
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

PYTHON = "/Users/maochundong/.hermes/hermes-agent/venv/bin/python3"

# ── HyperFrames Composition Rules ──────────────────────────────────────────────
# Root element needs: data-composition-id, data-duration, data-width, data-height
# Timed elements need: data-start, data-duration, class="clip"
# GSAP timeline registered on window.__timelines["main"] with { paused: true }
# Video elements must be muted; audio goes in separate <audio> elements

def build_composition_html(title, subtitle, emoji, cta, key_points, kp_emojis, bg_path, accent_color="#e85d4a"):
    """Build an HTML composition for HyperFrames rendering."""
    
    # Embed background image as base64
    bg_base64 = ""
    if bg_path and os.path.exists(bg_path):
        import base64
        with open(bg_path, "rb") as f:
            bg_base64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
    
    # Build key points HTML
    kp_items = ""
    if key_points:
        for i, (kp, kp_emoji) in enumerate(zip(key_points, kp_emojis if kp_emojis else [])):
            start = 2.0 + i * 0.8  # staggered entrance
            emoji_html = f"<span style='font-size:48px;margin-right:12px;'>{kp_emoji}</span>" if kp_emoji else ""
            kp_items += f'''
            <div class="kp-item clip" data-start="{start}" data-duration="3" data-track-index="0" style="
                display:flex;align-items:center;padding:16px 24px;margin:12px 0;
                background:rgba(255,255,255,0.15);border-radius:16px;
                backdrop-filter:blur(10px);border-left:4px solid {accent_color};
                transform:translateX(-60px);opacity:0;
            ">
                {emoji_html}<span style="font-size:32px;color:#fff;font-weight:600;">{kp}</span>
            </div>'''
    
    bg_style = f'background-image:url("{bg_base64}");background-size:cover;background-position:center 20%;' if bg_base64 else f'background:{accent_color};'
    
    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ 
    width:1080px; height:1920px; overflow:hidden; 
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "STHeiti", "Noto Sans CJK SC", sans-serif;
    background:#1a1a2e;
}}
.container {{
    width:1080px; height:1920px; position:relative;
    background:{bg_style};
}}
.overlay {{
    position:absolute; inset:0;
    background:linear-gradient(to bottom,
        {accent_color}cc 0%, {accent_color}88 15%, transparent 35%,
        transparent 65%, {accent_color}66 85%, {accent_color}cc 100%);
    pointer-events:none;
}}
.title-area {{
    position:absolute; top:120px; left:0; right:0; text-align:center; z-index:5;
    opacity:0; transform:scale(0.8);
}}
.title-main {{
    font-size:120px; font-weight:900; color:#fff;
    text-shadow:3px 5px 12px rgba(0,0,0,0.7);
    letter-spacing:4px; line-height:1.2;
    display:inline-flex; align-items:center; gap:20px;
}}
.title-emoji {{ font-size:110px; filter:drop-shadow(3px 4px 8px rgba(0,0,0,0.5)); }}
.subtitle {{
    font-size:56px; font-weight:700; color:#ffd4c8;
    text-shadow:2px 3px 8px rgba(0,0,0,0.5);
    margin-top:20px;
}}
.keypoints-area {{
    position:absolute; top:550px; left:60px; right:60px; z-index:5;
}}
.kp-item {{
    display:flex; align-items:center; padding:16px 24px; margin:12px 0;
    background:rgba(255,255,255,0.15); border-radius:16px;
    backdrop-filter:blur(10px); border-left:4px solid {accent_color};
}}
.cta-area {{
    position:absolute; bottom:200px; left:0; right:0; text-align:center; z-index:5;
    opacity:0; transform:translateY(30px);
}}
.cta-text {{
    font-size:52px; font-weight:800; color:#fff;
    text-shadow:3px 4px 10px rgba(0,0,0,0.6);
    display:inline-flex; align-items:center; gap:14px;
}}
.cta-emoji {{ font-size:50px; }}
.cta-btn {{
    display:inline-flex; align-items:center; gap:16px;
    padding:28px 72px; border-radius:70px;
    background:{accent_color}; margin-top:30px;
    font-size:40px; font-weight:800; color:#fff;
    box-shadow:0 8px 30px rgba(0,0,0,0.4);
    text-shadow:0 2px 4px rgba(0,0,0,0.3);
}}
.brand {{
    position:absolute; bottom:60px; right:60px;
    font-size:28px; color:rgba(255,255,255,0.5); z-index:5;
}}
</style>
</head>
<body>
<div class="container">
    <div class="overlay"></div>
    
    <div class="title-area">
        <div class="title-main">
            <span>{title}</span>
            <span class="title-emoji">{emoji}</span>
        </div>
        <div class="subtitle">{subtitle}</div>
    </div>
    
    <div class="keypoints-area">
        {kp_items}
    </div>
    
    <div class="cta-area">
        <div class="cta-text">
            <span>{cta}</span>
        </div>
        <div class="cta-btn">
            <span class="cta-emoji">💬</span>
            <span>来聊聊你的故事</span>
        </div>
    </div>
    
    <div class="brand">小红书 · 情绪树洞</div>
</div>

<script>
// Register GSAP timeline with HyperFrames
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = {{ paused: true }};

const tl = gsap.timeline({{
    paused: true,
    onUpdate: function() {{
        if (window.__hyperframes) {{
            window.__hyperframes.tick(tl.time());
        }}
    }}
}});

// Title entrance (0-1.5s)
tl.to(".title-area", {{
    opacity: 1, scale: 1, duration: 1.2, ease: "power3.out"
}}, 0);

// Key points stagger entrance (2-5s)
tl.to(".kp-item", {{
    x: 0, opacity: 1, duration: 0.5, ease: "power2.out",
    stagger: 0.3
}}, 2.0);

// CTA entrance (6-7.5s)
tl.to(".cta-area", {{
    opacity: 1, y: 0, duration: 1, ease: "power2.out"
}}, 6.0);

// Subtle pulse on CTA button (7.5-8s)
tl.to(".cta-btn", {{
    scale: 1.03, duration: 0.3, yoyo: true, repeat: 2
}}, 7.5);

window.__timelines["main"] = tl;
</script>
</body>
</html>''')
    
    return "".join(html_parts)


def render_hyperframes(project_dir, output_path, composition="index.html", fps=30, duration=8):
    """Render HyperFrames composition to MP4."""
    
    # Initialize HyperFrames project
    print(f"  🎬 Initializing HyperFrames project...")
    result = subprocess.run(
        ["npx", "hyperframes", "init", project_dir, "--skip-skills", "--non-interactive"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        # Project may already exist, that's fine
        print(f"  ⚠️  Init output: {result.stderr.strip()}")
    
    # Copy composition to project
    src = os.path.join(project_dir, "index.html")
    if os.path.exists(src):
        os.remove(src)
    
    # Move our HTML to the project's index.html
    composition_path = os.path.join(project_dir, "index.html")
    print(f"  📝 Writing composition to {composition_path}")
    
    return composition_path


def main():
    parser = argparse.ArgumentParser(description="HyperFrames video renderer for Xiaohongshu")
    parser.add_argument("--title", required=True, help="Main title text")
    parser.add_argument("--subtitle", default="", help="Subtitle text")
    parser.add_argument("--emoji", default="😭", help="Primary emoji")
    parser.add_argument("--cta", default="你家娃也这样吗？", help="Call-to-action text")
    parser.add_argument("--key-points", nargs="+", default=[], help="Key point texts")
    parser.add_argument("--kp-emojis", nargs="+", default=[], help="Key point emojis")
    parser.add_argument("--bg", default="", help="Background image path")
    parser.add_argument("--accent", default="#e85d4a", help="Accent color hex")
    parser.add_argument("--output", default="/tmp/xhs_video.mp4", help="Output MP4 path")
    parser.add_argument("--duration", type=float, default=8.0, help="Video duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Frame rate")
    args = parser.parse_args()
    
    # Create temp project
    with tempfile.TemporaryDirectory(prefix="xhs_hf_") as tmpdir:
        print(f"🎬 Generating video: {args.title}")
        print(f"  Subtitle: {args.subtitle}")
        print(f"  Key points: {args.key_points}")
        print(f"  BG: {args.bg or '(none)'}")
        
        # Build HTML composition
        html = build_composition_html(
            title=args.title,
            subtitle=args.subtitle,
            emoji=args.emoji,
            cta=args.cta,
            key_points=args.key_points,
            kp_emojis=args.kp_emojis,
            bg_path=args.bg,
            accent_color=args.accent,
        )
        
        # Write to project
        project_dir = os.path.join(tmpdir, "project")
        os.makedirs(project_dir, exist_ok=True)
        index_path = os.path.join(project_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        # Initialize HyperFrames
        print(f"  📦 Initializing HyperFrames project...")
        result = subprocess.run(
            ["npx", "hyperframes", "init", project_dir, "--skip-skills", "--non-interactive"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"  ⚠️  Init stderr: {result.stderr.strip()[:200]}")
        
        # Write composition (overwrite the scaffolded one)
        with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        
        # Lint first
        print(f"  ✅ Linting composition...")
        lint_result = subprocess.run(
            ["npx", "hyperframes", "lint", project_dir],
            capture_output=True, text=True, timeout=60
        )
        if lint_result.returncode != 0:
            print(f"  ⚠️  Lint warnings:")
            print(f"  {lint_result.stdout.strip()[:500]}")
            print(f"  {lint_result.stderr.strip()[:500]}")
        
        # Render
        print(f"  🎞️  Rendering to MP4 ({args.fps}fps, {args.duration}s)...")
        render_cmd = [
            "npx", "hyperframes", "render",
            project_dir,
            "-o", args.output,
            "--fps", str(args.fps),
            "--composition", "index.html",
        ]
        
        start_time = time.time()
        result = subprocess.run(render_cmd, capture_output=True, text=True, timeout=300)
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"  ❌ Render failed!")
            print(f"  STDOUT: {result.stdout.strip()[:1000]}")
            print(f"  STDERR: {result.stderr.strip()[:1000]}")
            sys.exit(1)
        
        print(f"  ✅ Rendered in {elapsed:.1f}s → {args.output}")
        
        # Verify output
        if os.path.exists(args.output):
            size_mb = os.path.getsize(args.output) / (1024 * 1024)
            print(f"  📁 Output size: {size_mb:.2f} MB")
        else:
            print(f"  ⚠️  Output file not found at {args.output}")
            # Check renders directory
            renders_dir = os.path.join(project_dir, "renders")
            if os.path.exists(renders_dir):
                files = os.listdir(renders_dir)
                if files:
                    latest = max(files)
                    new_path = os.path.join(renders_dir, latest)
                    print(f"  📁 Found in renders/: {new_path}")
                    subprocess.run(["cp", new_path, args.output])


if __name__ == "__main__":
    main()
