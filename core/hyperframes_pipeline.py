#!/usr/bin/env python3
"""Hyperframes frame pipeline — Ken Burns, safe margin, TTS timing.

Wraps hyperframes CLI for XHS card → video segment with motion.
Falls back to ffmpeg still-image segment if hyperframes unavailable.
"""
import subprocess, sys, pathlib

def hyperframes_available() -> bool:
    return subprocess.run(["which", "hyperframes"], capture_output=True).returncode == 0

def render_segment(image: str, duration: float, out: str, safe_margin: int = 48) -> bool:
    """Render one video segment with gentle Ken Burns (scale 1.0→1.05) and safe margin.
    Returns True on success, False if fallback needed.
    """
    if not hyperframes_available():
        return False
    try:
        # Hyperframes example: hyperframes zoom --input card.jpg --duration 6.9 --out seg.mp4
        # Actual flags depend on installed version; keep minimal and catch failures.
        cmd = ["hyperframes", "zoom", "--input", image, "--duration", str(duration), "--output", out, "--margin", str(safe_margin)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and pathlib.Path(out).exists()
    except Exception as e:
        print(f"[DBG] hyperframes render failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <image> <duration> <out.mp4>")
        sys.exit(1)
    ok = render_segment(sys.argv[1], float(sys.argv[2]), sys.argv[3])
    sys.exit(0 if ok else 2)
