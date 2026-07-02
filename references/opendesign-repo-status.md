# Open Design Repo Status

## Local Clone
- Path: `/Users/maochundong/open-design/`
- Remotes: GitHub `nexu-io/open-design`
- Contains: `skills/card-xiaohongshu` template directory

## Build Status (2026-06-21)
- `node_modules` missing
- Node v22.22.2 installed; repo requires ~24.x
- `pnpm` not installed
- `od` CLI not built
- Build steps (not yet run):
```bash
cd /Users/maochundong/open-design
nvm install 24
nvm use 24
corepack enable
pnpm install
pnpm --filter @open-design/daemon build
```

## card-xiaohongshu Skill Spec
- Output: 1080×1440 (3:4) vertical cards
- Multi-card layout: 3–18 images, scrollable
- Style: Xiaohongshu-feel knowledge card templates
- Use with: `opendesign convert -i <file.octopus> -o <output.png>` once daemon is built

## OpenDesign CLI (v0.3.0)
- Installed via npm but daemon not running
- `opendesign open <path>` — GUI viewer (do NOT use in cron)
- `opendesign convert -i <octopus> -o <png>` — headless conversion (correct cron tool)
