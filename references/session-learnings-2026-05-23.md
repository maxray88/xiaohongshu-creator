# Session Learnings 2026-05-23 — Cover Optimizations for Realism Niche

## Context
- 用户：职场搞钱与搞副业（现实主义）博主从0-1起号规划
- 需求：生成Day1封面（S6手绘风）并发布
- 挑战：封面字体、布局、代码泄露等问题

## 1. Cover v5 最终规格（无重叠、无泄露）

### Layout
- `.kp-wrap` top: **540px** (避开头标题换行区域)
- `.title-wrap` top: 70px
- `.cta-wrap` bottom: 60px
- 左右边距：左侧 80px，右侧 80px（关键点区域）

### Typography
- `.title-main`: **130px** (品黑/STHeiti) + 2px描边 (#C9A66B) + 光晕
- `.title-main .kw`: **150px** 关键词橙色
- `.kp-text`: **60px** (关键点正文，带1px描边)
- `.kp-text .kw`: **70px** 关键词橙色 + 底部装饰线
- `.kp-badge`: 50×50px，字体 22px

### Color Accents
- 标题描边: `#C9A66B`
- 标题阴影: `rgba(200,150,100,0.2)`
- 关键词橙色: `#e07850`
- 关键词装饰线: `rgba(224,120,80,0.2)`

### 间距与圆角
- `.kp-card` padding: `12px 20px`
- 卡片间距: `12px`
- 卡片圆角: `6px`
- 左强调边框: `6px solid #e8a87c`

## 2. 关键词高亮处理（避免CSS泄露）

问题：在生成HTML时同时使用 `**` 和 `< >` 替换导致已生成的 `<span class="kw">` 被错误二次替换，出现 `span class="kw"` 字符串。

**修复**：只使用 `**` 标记法，避免同时应用 `< >` 的正则替换。

代码示例：
```python
highlighted_point = re.sub(r'\*\*(.*?)\*\*', r'<span class="kw">\1</span>', point)
# 移除对尖括号的处理
```

## 3. 标题与关键点重叠排查

现象：标题过长时自动换行，而关键点区域起始位置 (`top: 460px`) 不足以避开标题底边，导致视觉遮挡。

解决步骤：
1. 估算标题高度 = 标题字号 × 行高 + 副标题高度 + 装饰线
2. 设置 `.kp-wrap { top: 标题高度 + 底部安全间距 }` (建议 start ≥ 500px)
3. 在 v5 中取 `top: 540px` 确保安全。

## 4. 金额快速批量修改技巧

用户将“100天攒1万”改为“10万”，需要更新：
- 标题关键词
- 正文若干处（目标金额、每日平均）
- 关键点第一条
- 标签中的话题

使用方法：
```bash
# 使用 sed 批量替换 post_data.json（或内容文件）
sed -i '' 's/1万/10万/g' /tmp/xhs_day1/content/post_data.json
sed -i '' 's/100天攒1万/100天攒10万/g' /tmp/xhs_day1/content.txt
```

或者直接在agent中重生成内容。

## 5. v5 完整 CSS（可直接嵌入）

```css
/* v5 complete CSS */
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:1080px; height:1440px; overflow:hidden; }
.cover { width:1080px; height:1440px; position:relative; background:#faf6f1; font-family:"PingFang SC","STHeiti","Hiragino Sans GB",sans-serif; }
.paper {
  position:absolute; inset:0;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(255,200,150,0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 80%, rgba(150,200,255,0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(255,220,170,0.05) 0%, transparent 60%);
}
.title-wrap {
  position:absolute; top:70px; left:60px; right:60px; text-align:center; z-index:5;
}
.title-main {
  font-size:130px; font-weight:900; color:#2a2520; line-height:1.2; letter-spacing:2px;
  transform:rotate(-0.8deg);
  -webkit-text-stroke:2px solid #C9A66B;
  text-shadow: 0 0 10px rgba(200,150,100,0.2), 0 0 6px rgba(200,150,100,0.15);
}
.title-main .kw {
  color:#e07850; font-size:150px; text-shadow: 2px 3px 0px rgba(224,120,80,0.15);
  position:relative;
}
.title-main .kw::after {
  content:''; position:absolute; bottom:-4px; left:-4px; right:-4px; height:8px;
  background:rgba(224,120,80,0.25); border-radius:4px; transform:rotate(-0.5deg);
}
.title-line {
  width:280px; height:8px; margin:10px auto 0;
  background:linear-gradient(90deg, transparent 0%, #e8a87c 30%, #d4956b 70%, #e8a87c 100%);
  border-radius:4px; transform:rotate(-0.5deg); opacity:0.8;
}
.title-sub {
  font-size:40px; color:#9a8060; margin-top:12px; font-weight:600; transform:rotate(0.5deg);
}
.kp-wrap {
  position:absolute; top:540px; left:80px; right:80px; z-index:5;
  display:flex; flex-direction:column; gap:12px;
}
.kp-card {
  display:flex; align-items:center; justify-content:center; gap:16px;
  padding:12px 20px;
  background:#fffef9; border-radius:6px;
  box-shadow: 2px 3px 10px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.02);
  transform:rotate(var(--r,0deg)); border-left:6px solid var(--c,#e8a87c);
}
.kp-badge {
  width:50px; height:50px; border-radius:50%;
  background:var(--cb,#fef3e8); color:var(--c,#e8a87c);
  font-size:22px; font-weight:900;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
  border:2.5px dashed var(--c,#e8a87c);
}
.kp-text {
  font-size:60px; color:#3a3530; font-weight:700; line-height:1.35;
  -webkit-text-stroke:1px solid #C9A66B;
  text-shadow: 0 0 8px rgba(200,150,100,0.15);
}
.kp-text .kw {
  color:var(--kwc,#e07850); font-weight:900; font-size:70px;
  position:relative; text-shadow: 1px 1px 0px rgba(224,120,80,0.1);
}
.kp-text .kw::after {
  content:''; position:absolute; bottom:-3px; left:-3px; right:-3px; height:6px;
  background:rgba(224,120,80,0.2); border-radius:3px; transform:rotate(-0.8deg);
}
.cta-wrap {
  position:absolute; bottom:60px; left:50px; right:50px; text-align:center; z-index:5;
}
.cta-inner {
  display:inline-block; padding:20px 56px;
  background:#2a2520; border-radius:10px; transform:rotate(-1.2deg);
  box-shadow:5px 5px 0px rgba(0,0,0,0.08);
}
.cta-text { font-size:36px; color:#fff; font-weight:700; letter-spacing:1px; }
.brand-mark { position:absolute; bottom:22px; right:35px; font-size:22px; color:rgba(0,0,0,0.12); font-weight:600; transform:rotate(-2deg); }
```

---

## Related References
- `cover-style-s6-optimized.md` — S6 手绘风格规范
- `treehole-strategy.md` — 内容策略（虽为树洞，但封面技术可复用）
