#!/bin/bash
# Push skill updates to GitHub
cd ~/.hermes/skills/xiaohongshu-creator
git add -A
git commit -m "${1:-skill update}"
git push
