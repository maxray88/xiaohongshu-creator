---
name: xiaohongshu-content-gen
description: |
  Generate Xiaohongshu (小红书) style content: inspiring titles, engaging stories,
  and trending hashtags. Use this skill when creating content for Xiaohongshu posts.
---

# Xiaohongshu Content Generator

Generate authentic, engaging Xiaohongshu-style content that resonates with the platform's audience.

## Content Style Guide

### Title Patterns (pick one)
- **Emotional hook**: "后悔没早点知道！..." / "天呐！终于找到了..."
- **Number list**: "3个技巧让你..." / "5分钟学会..."
- **Question**: "你还在为...发愁吗？"
- **Transformation**: "从...到...我只用了..."
- **Secret share**: "偷偷告诉你们..." / "压箱底的...分享"
- **Relatable**: "姐妹们！这个真的绝了！" / "救命！太好用了！"

### Body Story Structure
1. **Hook** (1-2 sentences): Grab attention, state the problem or excitement
2. **Personal experience** (2-3 sentences): Share your genuine story/feeling
3. **Value delivery** (2-4 sentences): Tips, steps, or key insights
4. **Emotional close** (1-2 sentences): Warm ending with call to engagement
5. **Hashtags** (5-10): Mix of trending + niche + content-specific

### Tone & Style
- **Warm & conversational** — like talking to a close friend
- **Use emojis naturally** ✨🎉💕🔥 (not excessively)
- **Short paragraphs** — 1-3 sentences each, easy to scan
- **Authentic voice** — avoid corporate/marketing language
- **Include personal details** — "我之前..." "用了一周后发现..."
- **Engagement hooks** — "你们觉得呢？" "评论区告诉我～"

### Hashtag Strategy
Always include a mix:
- **Broad tags**: #小红书 #好物分享 #生活分享
- **Niche tags**: Match the specific topic (e.g., #护肤心得 #穿搭日记)
- **Trending tags**: Check current trending topics
- **Content tags**: Describe the specific content

## Generation Process

When asked to generate content:

1. **Understand the topic** — What is the post about?
2. **Pick a title pattern** — Choose from the patterns above
3. **Write the story** — Follow the body structure
4. **Add hashtags** — 5-10 relevant hashtags
5. **Review** — Ensure it sounds natural and engaging

## Example Output Format

```
标题：后悔没早点发现！这个护肤方法真的绝了✨

正文：
姐妹们！今天必须分享这个让我惊到的护肤方法！💕

之前我的皮肤状态一直很差，暗沉、毛孔粗大，试了好多产品都没效果。后来一个朋友推荐了这个方法，抱着试试看的心态用了一周...

结果真的惊艳到我！皮肤明显透亮了，毛孔也细腻了好多！

具体方法👇
1️⃣ 第一步：...
2️⃣ 第二步：...
3️⃣ 第三步：...

最重要的是坚持！效果真的看得见～

你们有什么护肤心得吗？评论区分享一下吧！❤️

#护肤心得 #好物分享 #变美日记 #小红书 #护肤方法 #素颜也好看
```

## Language
- Default to **Chinese (Simplified)** for Xiaohongshu content
- Match the user's language preference if specified
- Keep the authentic Xiaohongshu voice regardless of language

## Viral Content Formula (User-Approved)

The following 7-step formula consistently produces viral Xiaohongshu posts:

1. **Past self with negative opinion** — Start with a relatable "before" state
2. **Life trigger / realization** — What changed? A moment of insight
3. **Reframe / insight flip** — The "aha!" moment that flips the narrative
4. **Numbered evidence list** — 3-7 concrete, scannable points
5. **Emotional payoff sentence** — A warm, resonant closing line
6. **Universal identity connection** — "All moms feel this" / "Anyone who..."
7. **Personal story CTA** — Ask a personal question (not yes/no) to drive comments

### Title Patterns That Work
- **Emotional hook**: "后悔没早点知道！..." / "天呐！终于找到了..."
- **Number list**: "{}个技巧让你..." / "分钟学会" / "{}大真相"
- **Question**: "你还在为...发愁吗？"
- **Transformation**: "从...到...我只用了..."
- **Secret share**: "偷偷告诉你们..." / "压箱底的...分享"
- **Relatable**: "姐妹们！这个真的绝了！" / "救命！太好用了！"
- **FOMO**: "不看你就亏了" / "赶紧收藏" / "错过后悔一年"

### CTA Principles
- NEVER ask yes/no questions — they kill engagement
- ALWAYS ask for personal stories or opinions
- Examples: "你家娃也这样吗？" / "你妈妈也是超人吗？" / "评论区说说你的故事"

### Hashtag Mix (10 total)
- 2-3 broad tags: #小红书 #好物分享 #生活分享
- 3-4 niche tags: topic-specific
- 2-3 trending/emotional tags: #感动 #治愈 #太真实了
- 1-2 content-specific tags

## Automated Generation

For automated content + cover generation, use:
```bash
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \
    --topic "Topic here" --style "emotional" --emoji "😭"
```

The script generates 5 ranked titles, full body, 10 hashtags, 3 cover designs, and auto-invokes the image pipeline.
