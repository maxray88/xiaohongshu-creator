"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ _cron_compress2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Compress images more aggressively to get total raw < 600KB."""
import json
import os
from PIL import Image

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
D = "20260718"
M2 = f"{BASE}/day_{D}_day12_v2/manifest.json"
m2 = json.load(open(M2))
img_dir = f"{BASE}/day_{D}_day12_v2/images"

compressed_dir = f"{BASE}/day_{D}_day12_v2/compressed_aggressive"
os.makedirs(compressed_dir, exist_ok=True)

TARGET_TOTAL_RAW = 550_000  # aim for ~750KB base64
quality = 60

compressed_images = []
total_raw = 0
for c in m2['cards']:
    src = os.path.join(img_dir, c['file'])
    orig_size = os.path.getsize(src)
    dst = os.path.join(compressed_dir, c['file'])
    img = Image.open(src)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Also try reducing resolution if total is still too high
    for attempt_q in range(55, 15, -5):
        img.save(dst, 'JPEG', quality=attempt_q, optimize=True)
        s = os.path.getsize(dst)
        if s <= 80_000:
            break
    
    final_size = os.path.getsize(dst)
    total_raw += final_size
    print(f"{c['file']}: {orig_size} -> {final_size} bytes (q={attempt_q})")
    compressed_images.append(dst)

print(f"\nTotal raw size: {total_raw} bytes (~{total_raw * 4 // 3 // 1024}KB base64)")
print("\n=== COMPRESSED IMAGE PATHS ===")
print(",".join(compressed_images))
