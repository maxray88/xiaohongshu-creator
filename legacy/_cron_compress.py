"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ _cron_compress.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""压缩图片到 150KB 以下，专门为小红书发布优化。"""
import os
import sys
from PIL import Image

QUALITY_START = 85
TARGET_SIZE = 145 * 1024  # 145KB (留 5KB 余量)

def compress_image(img_path, quality=QUALITY_START):
    """Compress a single image, returns (output_path, new_size)."""
    img = Image.open(img_path)
    base, ext = os.path.splitext(img_path)
    out_path = f"{base}_compressed.jpg"

    # Convert RGBA/P to RGB
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.save(out_path, "JPEG", quality=quality, optimize=True)
    new_size = os.path.getsize(out_path)
    return out_path, new_size

def main():
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        # Default to today's v2 images
        target_dir = os.path.expanduser(
            "~/.hermes/data/xhs_treehole/day_20260723_day20_v2/images"
        )

    if not os.path.isdir(target_dir):
        print(f"[ERROR] Directory not found: {target_dir}")
        sys.exit(1)

    jpgs = sorted([f for f in os.listdir(target_dir)
                   if f.lower().endswith((".jpg", ".jpeg"))])
    if not jpgs:
        print(f"[ERROR] No JPGs found in {target_dir}")
        sys.exit(1)

    print(f"[INFO] Compressing {len(jpgs)} images in {target_dir}")
    results = []

    for jpg in jpgs:
        img_path = os.path.join(target_dir, jpg)
        orig_size = os.path.getsize(img_path)

        if orig_size < TARGET_SIZE:
            print(f"  ✓ {jpg}: {orig_size/1024:.0f}KB (already < 150KB)")
            results.append((jpg, orig_size, orig_size))
            continue

        quality = QUALITY_START
        compressed = None
        while quality >= 20:
            try:
                out_path, new_size = compress_image(img_path, quality)
                if new_size < TARGET_SIZE:
                    compressed = out_path
                    # Replace original with compressed
                    os.replace(out_path, img_path)
                    break
                quality -= 5
            except Exception as e:
                print(f"  [ERROR] {jpg}: {e}")
                break

        if compressed:
            final_size = os.path.getsize(img_path)
            print(f"  ✅ {jpg}: {orig_size/1024:.0f}KB → {final_size/1024:.0f}KB (q={quality})")
            results.append((jpg, orig_size, final_size))
        else:
            print(f"  ❌ {jpg}: {orig_size/1024:.0f}KB → couldn't compress below 150KB")

    # Summary
    print(f"\n{'='*50}")
    print(f"Summary: {len([r for r in results if r[2] < TARGET_SIZE])}/{len(results)} compressed OK")
    total_before = sum(r[1] for r in results)
    total_after = sum(r[2] for r in results)
    print(f"Total: {total_before/1024:.0f}KB → {total_after/1024:.0f}KB ({'✓' if total_after < len(results)*TARGET_SIZE else '⚠ '})")

if __name__ == "__main__":
    main()
