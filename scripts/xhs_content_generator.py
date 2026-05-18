"""
Xiaohongshu Viral Content Generator - All-in-One
==================================================
Given a topic, generates:
  1. 5 viral title options (<=20 Chinese chars each)
  2. Full body content (hook -> story -> value -> CTA)
  3. 10 optimized hashtags
  4. Cover image descriptions
  5. Auto-invokes xhs_image_pipeline.py for cover generation

Usage:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \\
        --topic "蜡笔小新妈妈美伢的辛酸史" \\
        --output /tmp/xhs_post

    # With custom style:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \\
        --topic "Topic here" \\
        --style "funny" \\
        --emoji "😭" \\
        --output /tmp/xhs_post

Requirements: LLM access (via Hermes agent), requests, playwright, Pillow
"""

import argparse, asyncio, json, os, subprocess, sys, textwrap
from datetime import datetime


# ─── LLM Prompt Template ──────────────────────────────────────────────────────

# Template is loaded from the skill's templates directory.
# This allows updating the prompt without modifying the script.
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
_TEMPLATE_FILE = os.path.join(_TEMPLATE_DIR, "xhs_content_prompt_template.md")


def _load_prompt_template() -> str:
    """Load the content generation prompt template from the skill's templates directory."""
    if os.path.exists(_TEMPLATE_FILE):
        with open(_TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback: use embedded template (for backward compatibility)
    return _EMBEDDED_PROMPT_TEMPLATE


# Embedded fallback template (used when template file is not found)
_EMBEDDED_PROMPT_TEMPLATE = """# Role: Expert Xiaohongshu (Red) Content Creator & Viral Marketing Strategist

You are a top-tier influencer on Xiaohongshu (Red), known for creating viral posts that perfectly balance emotional resonance, sharp humor, and high aesthetic value.

## Topic
{topic}

## Task
Create a complete Xiaohongshu post for the topic above.

## Output Requirements

### 1. Eye-Catching Titles (5 options, each <=20 Chinese characters)
- Use "Clickbait" logic but keep it high-quality
- Incorporate numbers, emotional triggers (FOMO, curiosity, "life-changing"), or trending slang
- Rank by viral potential (best first)
- Each title MUST be 20 characters or fewer

### 2. Engaging Body Content
- **Tone:** Personal, sisterly/brotherly, witty, and relatable. Avoid sounding like a formal advertisement.
- **Structure:**
  - **Hook:** Start with a relatable pain point or a "wow" moment (1-2 sentences)
  - **Storytelling/Insights:** Mix humor with genuine emotion. Use short, punchy sentences. (3-5 sentences)
  - **Value List:** Numbered or bulleted list of key points (3-7 items)
  - **Emotional Close:** Warm ending that connects to the reader (1-2 sentences)
- **Formatting:** Use bullet points or numbered lists to make it scannable
- **Language:** Blend professional insights with Gen-Z internet slang
- **Emoji Magic:** Liberally use emojis to break up text and add personality (but keep it aesthetic, not messy)

### 3. Cover Image Suggestions (3 variants)
For each cover, describe:
- Background image search query (in English, for Bing search)
- Main title text (short, <=10 chars)
- Emoji to use
- Subtitle text
- CTA question
- Color mood (warm/cool, specific hex if possible)

### 4. Interaction & CTA
- End with a clever, low-friction question to force people to comment
- NOT a yes/no question - ask for personal stories or opinions

### 5. Optimized Hashtags (10 total)
- Mix of broad + niche + trending + content-specific
- Include 2-3 broad tags (#好物分享 #生活日常 etc.)
- Include 3-4 niche tags related to the topic
- Include 2-3 trending/emotional tags

## Output Format (STRICT JSON)

```json
{
  "titles": [
    {"rank": 1, "text": "标题1", "chars": 6, "viral_score": 95},
    {"rank": 2, "text": "标题2", "chars": 8, "viral_score": 90}
  ],
  "selected_title": "最佳标题",
  "body": "完整的正文内容(包含emoji)",
  "cta": "互动引导问题",
  "hashtags": ["#标签1", "#标签2"],
  "covers": [
    {
      "variant": 1,
      "search_query": "English search query for background image",
      "title": "封面标题",
      "emoji": "😭",
      "subtitle": "副标题",
      "cta": "互动问题",
      "color_mood": "#dc3c3c"
    }
  ]
}
```

## Important
- Output ONLY valid JSON, no markdown code fences, no extra text
- All text must be in Chinese (Simplified)
- Title character counts must be accurate (each <=20)
- Body content should be 200-500 characters
- Make it genuinely viral-worthy, not generic
"""


# ─── Title Patterns (for validation/enhancement) ──────────────────────────────

TITLE_PATTERNS = {
    "emotional": ["后悔没早点知道!", "天呐!终于找到了", "救命!太好用了", "姐妹们!这个真的绝了"],
    "number": ["{}个技巧让你", "分钟学会", "大真相", "个秘密"],
    "question": ["你还在为{}发愁吗?", "你知道{}吗?", "为什么{}?"],
    "transformation": ["从{}到{}我只用了", "逆袭{}我只用了"],
    "secret": ["偷偷告诉你们", "压箱底的{}分享", "我的{}秘密"],
    "fomo": ["不看你就亏了", "赶紧收藏", "错过后悔一年"],
}

VIRAL_FORMULA = [
    "(1) Past self with negative opinion",
    "(2) Life trigger / realization",
    "(3) Reframe / insight flip",
    "(4) Numbered evidence list",
    "(5) Emotional payoff sentence",
    "(6) Universal identity connection",
    "(7) Personal story CTA",
]


# ─── Hashtag Database ─────────────────────────────────────────────────────────

BROAD_HASHTAGS = [
    "#小红书", "#好物分享", "#生活分享", "#日常分享", "#经验分享",
    "#干货分享", "#种草", "#安利", "#打卡", "#推荐",
]

EMOTIONAL_HASHTAGS = [
    "#感动", "#治愈", "#暖心", "#泪目", "#破防了",
    "#太真实了", "#扎心了", "#共鸣", "#说到心坎", "#看哭了",
]

NICHE_TEMPLATES = {
    "anime": ["#动漫", "#二次元", "#动漫推荐", "#经典动漫", "#动漫角色"],
    "parenting": ["#育儿", "#宝妈", "#带娃", "#育儿经验", "#宝宝成长"],
    "family": ["#家庭", "#亲情", "#家人", "#温馨", "#家的味道"],
    "food": ["#美食", "#食谱", "#做饭", "#美食分享", "#家常菜"],
    "beauty": ["#护肤", "#美妆", "#变美", "#好物推荐", "#护肤心得"],
    "lifestyle": ["#生活", "#生活方式", "#品质生活", "#生活美学", "#日常"],
    "career": ["#职场", "#工作", "#成长", "#自我提升", "#职场干货"],
    "relationship": ["#恋爱", "#感情", "#爱情", "#情感", "#恋爱日常"],
    "health": ["#健康", "#养生", "#运动", "#健身", "#健康生活"],
    "travel": ["#旅行", "#旅游", "#出行", "#打卡", "#旅行攻略"],
}


# ─── Content Generator Class ──────────────────────────────────────────────────

class XiaohongshuContentGenerator:
    """Generates viral Xiaohongshu content from a topic."""

    def __init__(self, topic: str, style: str = "auto", emoji: str = ""):
        self.topic = topic
        self.style = style
        self.emoji = emoji
        self.result = {}

    def _build_prompt(self) -> str:
        """Build the LLM prompt from the template file."""
        template = _load_prompt_template()
        topic_with_style = self.topic
        if self.style != "auto":
            topic_with_style = f"{self.topic} (style: {self.style})"
        if self.emoji:
            topic_with_style += f" (emoji: {self.emoji})"
        return template.format(topic=topic_with_style)

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM via Hermes agent's execute_code or subprocess.
        Since this script runs in the agent context, we use the agent's
        built-in LLM by writing a temp file and asking the agent to process it.

        For standalone usage, this falls back to a template-based approach.
        """
        # Write prompt to temp file for agent to process
        prompt_file = "/tmp/xhs_content_prompt.txt"
        response_file = "/tmp/xhs_content_response.json"

        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Check if we are running inside the Hermes agent context
        # (the agent will handle this via its own LLM)
        # For standalone mode, return a signal for the agent to process
        return f"__AGENT_PROCESS__:{prompt_file}:{response_file}"

    def _parse_llm_response(self, raw: str) -> dict:
        """Parse LLM JSON response."""
        # Clean up response
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  WARNING: JSON parse error: {e}")
            print(f"  Raw response (first 500 chars): {raw[:500]}")
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {}

    def _validate_titles(self, titles: list) -> list:
        """Validate and fix titles."""
        validated = []
        for t in titles:
            text = t.get("text", "")
            chars = len(text)
            if chars > 20:
                print(f"  WARNING: Title too long ({chars} chars): '{text}' - truncating")
                text = text[:20]
                chars = 20
            t["text"] = text
            t["chars"] = chars
            validated.append(t)
        return validated

    def _enhance_hashtags(self, hashtags: list, topic: str) -> list:
        """Enhance hashtags with broad and emotional tags."""
        enhanced = list(hashtags) if hashtags else []

        # Add broad tags if not present
        for tag in BROAD_HASHTAGS[:3]:
            if tag not in enhanced:
                enhanced.append(tag)

        # Add emotional tags
        for tag in EMOTIONAL_HASHTAGS[:2]:
            if tag not in enhanced:
                enhanced.append(tag)

        # Detect niche from topic
        topic_lower = topic.lower()
        for niche, tags in NICHE_TEMPLATES.items():
            if niche in topic_lower or any(kw in topic_lower for kw in [niche]):
                for tag in tags[:2]:
                    if tag not in enhanced:
                        enhanced.append(tag)
                break

        return enhanced[:12]  # Max 12 hashtags

    def generate(self) -> dict:
        """
        Main generation method.
        Returns a dict with titles, body, hashtags, covers.
        """
        prompt = self._build_prompt()
        raw_response = self._call_llm(prompt)

        # Check if agent needs to process
        if raw_response.startswith("__AGENT_PROCESS__"):
            # Return the prompt for the agent to handle
            return {
                "__needs_agent_processing__": True,
                "prompt": prompt,
                "prompt_file": raw_response.split(":")[1],
                "response_file": raw_response.split(":")[2],
            }

        # Parse response
        data = self._parse_llm_response(raw_response)

        if not data:
            return {"error": "Failed to generate content", "raw": raw_response[:500]}

        # Validate and enhance
        if "titles" in data:
            data["titles"] = self._validate_titles(data["titles"])
        if "hashtags" in data:
            data["hashtags"] = self._enhance_hashtags(data["hashtags"], self.topic)

        self.result = data
        return data


# ─── Cover Pipeline Integration ───────────────────────────────────────────────

def run_image_pipeline(cover_designs: list, output_dir: str) -> list:
    """
    Invoke xhs_image_pipeline.py for each cover design.
    Returns list of generated cover file paths.
    """
    PYTHON = sys.executable
    pipeline_script = os.path.expanduser(
        "~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py"
    )

    if not os.path.exists(pipeline_script):
        print(f"  WARNING: Pipeline script not found: {pipeline_script}")
        return []

    covers = []
    for i, design in enumerate(cover_designs):
        query = design.get("search_query", "")
        title = design.get("title", "")
        emoji = design.get("emoji", "✨")
        subtitle = design.get("subtitle", "")
        cta = design.get("cta", "")

        if not query:
            print(f"  WARNING: Cover {i+1}: No search query, skipping")
            continue

        cover_output = os.path.join(output_dir, f"cover_{i+1}")
        os.makedirs(cover_output, exist_ok=True)

        cmd = [
            PYTHON, pipeline_script,
            "--query", query,
            "--title", title,
            "--emoji", emoji,
            "--subtitle", subtitle,
            "--cta", cta,
            "--output", cover_output,
            "--count", "5",
        ]

        print(f"\n  Cover {i+1}: {title} {emoji}")
        print(f"    Query: {query}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # Find generated covers
                for f in os.listdir(cover_output):
                    if f.endswith(".jpg") and "_preview" not in f:
                        covers.append(os.path.join(cover_output, f))
                print(f"    OK Cover generated")
            else:
                print(f"    FAIL Pipeline error: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"    FAIL Pipeline timeout")
        except Exception as e:
            print(f"    FAIL Pipeline exception: {e}")

    return covers


# ─── Output Formatting ────────────────────────────────────────────────────────

def format_post_output(data: dict, cover_paths: list = None) -> str:
    """Format the complete post output."""
    lines = []
    lines.append("=" * 60)
    lines.append("XIAOHONGSHU POST - READY TO PUBLISH")
    lines.append("=" * 60)

    # Titles
    lines.append("\nTITLE OPTIONS (ranked by viral potential):")
    lines.append("-" * 40)
    for t in data.get("titles", []):
        rank = t.get("rank", "?")
        text = t.get("text", "")
        chars = t.get("chars", len(text))
        score = t.get("viral_score", "?")
        lines.append(f"  {rank}. [{text}] ({chars} chars) [viral: {score}]")

    selected = data.get("selected_title", data.get("titles", [{}])[0].get("text", ""))
    lines.append(f"\n  SELECTED: [{selected}]")

    # Body
    lines.append("\nBODY CONTENT:")
    lines.append("-" * 40)
    body = data.get("body", "")
    lines.append(body)

    # CTA
    cta = data.get("cta", "")
    if cta:
        lines.append(f"\nCTA: {cta}")

    # Hashtags
    hashtags = data.get("hashtags", [])
    if hashtags:
        lines.append("\nHASHTAGS:")
        lines.append("-" * 40)
        lines.append(" ".join(hashtags))

    # Covers
    if cover_paths:
        lines.append("\nCOVER IMAGES:")
        lines.append("-" * 40)
        for p in cover_paths:
            size = os.path.getsize(p) // 1024 if os.path.exists(p) else 0
            lines.append(f"  {p} ({size}KB)")

    # Cover descriptions
    covers = data.get("covers", [])
    if covers:
        lines.append("\nCOVER DESIGN DESCRIPTIONS:")
        lines.append("-" * 40)
        for c in covers:
            lines.append(f"\n  Variant {c.get('variant', '?')}:")
            lines.append(f"    Search: {c.get('search_query', 'N/A')}")
            lines.append(f"    Title: {c.get('title', 'N/A')} {c.get('emoji', '')}")
            lines.append(f"    Subtitle: {c.get('subtitle', 'N/A')}")
            lines.append(f"    CTA: {c.get('cta', 'N/A')}")
            lines.append(f"    Color: {c.get('color_mood', 'N/A')}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ─── File Output ──────────────────────────────────────────────────────────────

def save_post_files(data: dict, output_dir: str, cover_paths: list = None):
    """Save all post files to output directory."""
    os.makedirs(output_dir, exist_ok=True)

    # Save content as text
    selected_title = data.get("selected_title", data.get("titles", [{}])[0].get("text", ""))
    body = data.get("body", "")
    hashtags = data.get("hashtags", [])
    cta = data.get("cta", "")

    content_text = f"{selected_title}\n\n{body}\n\n{cta}\n\n{' '.join(hashtags)}"
    content_path = os.path.join(output_dir, "content.txt")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content_text)

    # Save structured data as JSON
    json_path = os.path.join(output_dir, "post_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Save formatted output
    formatted = format_post_output(data, cover_paths)
    formatted_path = os.path.join(output_dir, "post_preview.txt")
    with open(formatted_path, "w", encoding="utf-8") as f:
        f.write(formatted)

    # Copy best cover to output dir
    if cover_paths:
        import shutil
        best_cover = cover_paths[0]
        if os.path.exists(best_cover):
            dest = os.path.join(output_dir, "cover_best.jpg")
            shutil.copy2(best_cover, dest)

    return {
        "content": content_path,
        "json": json_path,
        "preview": formatted_path,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Xiaohongshu Viral Content Generator - All-in-One",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate content + covers for a topic:
  %(prog)s --topic "蜡笔小新妈妈美伢的辛酸史" --output /tmp/xhs_post

  # Content only (no image generation):
  %(prog)s --topic "Topic" --no-images

  # With custom style and emoji:
  %(prog)s --topic "Topic" --style "funny" --emoji "😭"

  # Use pre-generated content JSON:
  %(prog)s --from-json /tmp/xhs_post/post_data.json --output /tmp/xhs_post
        """
    )

    parser.add_argument("--topic", type=str, help="Post topic (Chinese or English)")
    parser.add_argument("--style", default="auto", choices=["auto", "funny", "emotional", "inspirational", "savage", "warm"],
                        help="Content style (default: auto)")
    parser.add_argument("--emoji", default="", help="Primary emoji for the post")
    parser.add_argument("--output", default="/tmp/xhs_post", help="Output directory")
    parser.add_argument("--no-images", action="store_true", help="Skip cover image generation")
    parser.add_argument("--from-json", type=str, help="Load content from existing JSON file")
    parser.add_argument("--agent-prompt", action="store_true", help="Output the LLM prompt for agent processing")

    args = parser.parse_args()

    print("Xiaohongshu Viral Content Generator")
    print("=" * 60)

    # Load or Generate Content
    if args.from_json:
        print(f"\nLoading content from: {args.from_json}")
        with open(args.from_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif args.agent_prompt:
        gen = XiaohongshuContentGenerator(args.topic, args.style, args.emoji)
        prompt = gen._build_prompt()
        print(prompt)
        return
    else:
        print(f"\nTopic: {args.topic}")
        print(f"Style: {args.style}")
        if args.emoji:
            print(f"Emoji: {args.emoji}")

        gen = XiaohongshuContentGenerator(args.topic, args.style, args.emoji)
        data = gen.generate()

        if data.get("__needs_agent_processing__"):
            print("\nAgent processing required.")
            print(f"Prompt saved to: {data['prompt_file']}")
            print(f"Response will be saved to: {data['response_file']}")
            print("\nPrompt:")
            print("-" * 40)
            print(data["prompt"])
            return

    if "error" in data:
        print(f"\nError: {data['error']}")
        sys.exit(1)

    # Display Results
    print("\n" + format_post_output(data))

    # Save Files
    os.makedirs(args.output, exist_ok=True)
    files = save_post_files(data, args.output)
    print(f"\nFiles saved to: {args.output}")
    for name, path in files.items():
        print(f"  {name}: {path}")

    # Generate Cover Images
    cover_paths = []
    if not args.no_images:
        covers = data.get("covers", [])
        if covers:
            print(f"\nGenerating {len(covers)} cover images...")
            cover_paths = run_image_pipeline(covers, args.output)
            if cover_paths:
                print(f"\n  {len(covers)} covers generated:")
                for p in cover_paths:
                    print(f"    {p}")
            else:
                print("\n  No covers generated. Use --no-images to skip.")

    # Final Summary
    print("\n" + "=" * 60)
    print("POST READY!")
    print("=" * 60)
    print(f"\nTitle: {data.get('selected_title', 'N/A')}")
    print(f"Content: {files['content']}")
    if cover_paths:
        print(f"Best cover: {os.path.join(args.output, 'cover_best.jpg')}")
    print(f"\nPublish command:")
    print(f"  PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3")
    print(f"  $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \\")
    print(f"    --title \"{data.get('selected_title', '')}\" \\")
    print(f"    --content \"$(cat {files['content']})\" \\")
    if cover_paths:
        print(f"    --images {os.path.join(args.output, 'cover_best.jpg')}")


if __name__ == "__main__":
    main()
