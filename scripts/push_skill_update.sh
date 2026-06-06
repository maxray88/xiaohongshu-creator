#!/usr/bin/env bash
set -euo pipefail
skill_src="/Users/maochundong/.hermes/skills/xiaohongshu-creator"
skill_dst="/Users/maochundong/.hermes/skills/social-media/make-money-xiaohongshu/skill"
mkdir -p "$skill_dst"
cp -f "$skill_src"/SKILL.md "$skill_dst"/SKILL.md
cp -f "$skill_src"/templates/xhs_content_prompt_template.md "$skill_dst"/templates/xhs_content_prompt_template.md
echo "SYNCED $skill_src -> $skill_dst"
