# GitHub Upload Workflow

## Creating a New Repository

```bash
# 1. Install gh CLI (if not available)
brew install gh

# 2. Create repo via API (avoids gh auth read:org requirement)
curl -s -X POST https://api.github.com/user/repos \
  -H "Authorization: token <PAT>" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"name":"<repo-name>","description":"...","private":false}'

# 3. Init and push
cd <skill-directory>
git init
git config user.name "Chundong Mao"
git config user.email "maoyidong@gmail.com"

# Create .gitignore first
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.DS_Store
*.swp
*.swo
.env
cookies.json
/tmp/
EOF

git add -A
git commit -m "initial commit"
git remote add origin https://github.com/<user>/<repo>.git
git branch -M main
git push -u origin main
```

## PAT Requirements

- `repo` scope (full control) or `public_repo` for public repos
- `read:org` NOT needed for repo creation via API
- Don't embed PAT in remote URL

## User's GitHub

- Username: `maxray88`
- Repo: https://github.com/maxray88/xiaohongshu-creator
