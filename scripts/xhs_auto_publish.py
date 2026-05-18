#!/usr/bin/env python3
"""
Xiaohongshu Auto-Publish — Full Pipeline Orchestrator
======================================================
One command from topic to published post.

Pipeline:
  1. xhs_content_generator.py  → Generate viral content (titles, body, hashtags, cover designs)
  2. xhs_image_pipeline.py     → Search images + render covers
  3. xhs_publish.py            → Publish to Xiaohongshu via CDP

Usage:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_auto_publish.py \\
        --topic "蜡笔小新妈妈美伢的辛酸史"

    # With style and emoji:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_auto_publish.py \\
        --topic "Topic" --style "emotional" --emoji "😭"

    # Skip content generation (use existing):
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_auto_publish.py \\
        --from-json /tmp/xhs_post/post_data.json

    # Content only (dry run, no publish):
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_auto_publish.py \\
        --topic "Topic" --dry-run

Requirements: requests, playwright, Pillow, Chrome with CDP on port 9222
"""
import argparse, json, os, subprocess, sys, shutil

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable


def run_step(description: str, cmd: list, timeout: int = 300) -> bool:
    """Run a pipeline step. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"  Command: {' '.join(cmd[:5])}...")
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=timeout)
        if result.returncode == 0:
            print(f"  ✅ {description} — DONE")
            return True
        else:
            print(f"  ❌ {description} — FAILED (exit code {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ {description} — TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"  ❌ {description} — ERROR: {e}")
        return False


def step1_generate_content(topic: str, style: str, emoji: str, output_dir: str) -> str:
    """Step 1: Generate viral content. Returns path to post_data.json."""
    content_output = os.path.join(output_dir, "content")
    os.makedirs(content_output, exist_ok=True)

    cmd = [
        PYTHON,
        os.path.join(SCRIPTS_DIR, "xhs_content_generator.py"),
        "--topic", topic,
        "--style", style,
        "--output", content_output,
    ]
    if emoji:
        cmd.extend(["--emoji", emoji])

    # Content generation needs LLM — output the prompt for agent processing
    # The script outputs __AGENT_PROCESS__ signal when LLM is needed
    print(f"\n{'='*60}")
    print(f"🚀 Step 1: Generating viral content for '{topic}'")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Check if agent processing is needed
    if "__AGENT_PROCESS__" in result.stdout or "__AGENT_PROCESS__" in result.stderr:
        print("  🤖 LLM processing required — outputting prompt for agent...")
        # Extract and print the prompt
        for line in result.stdout.split('\n'):
            if line.strip() and not line.startswith('{'):
                print(line)
        # Also check stderr
        for line in result.stderr.split('\n'):
            if line.strip():
                print(line)

        # Write prompt to file for agent
        prompt_file = os.path.join(content_output, "_agent_prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        print(f"  📄 Prompt saved to: {prompt_file}")
        print(f"\n  ⚠️  Agent must process this prompt and save result to:")
        print(f"     {os.path.join(content_output, 'post_data.json')}")
        return None

    # Check if JSON was generated directly
    json_path = os.path.join(content_output, "post_data.json")
    if os.path.exists(json_path):
        print(f"  ✅ Content generated: {json_path}")
        return json_path

    # Check for agent-processed result
    agent_result = os.path.join(content_output, "post_data.json")
    if os.path.exists(agent_result):
        print(f"  ✅ Agent-processed content found: {agent_result}")
        return agent_result

    print(f"  ❌ Content generation failed")
    print(f"  stdout: {result.stdout[:500]}")
    print(f"  stderr: {result.stderr[:500]}")
    return None


def step2_generate_covers(post_data_path: str, output_dir: str) -> list:
    """Step 2: Generate cover images from cover designs. Returns list of cover paths."""
    with open(post_data_path, "r", encoding="utf-8") as f:
        post_data = json.load(f)

    covers = post_data.get("covers", [])
    if not covers:
        print("  ⚠️  No cover designs in post data")
        return []

    cover_paths = []
    for i, design in enumerate(covers):
        query = design.get("search_query", "")
        title = design.get("title", "")
        emoji = design.get("emoji", "✨")
        subtitle = design.get("subtitle", "")
        cta = design.get("cta", "")

        if not query:
            print(f"  ⚠️  Cover {i+1}: No search query, skipping")
            continue

        cover_output = os.path.join(output_dir, f"cover_{i+1}")
        os.makedirs(cover_output, exist_ok=True)

        cmd = [
            PYTHON,
            os.path.join(SCRIPTS_DIR, "xhs_image_pipeline.py"),
            "--query", query,
            "--title", title,
            "--emoji", emoji,
            "--subtitle", subtitle,
            "--cta", cta,
            "--output", cover_output,
            "--count", "5",
        ]

        success = run_step(
            f"Step 2.{i+1}: Generating cover {i+1} — {title} {emoji}",
            cmd, timeout=180
        )

        if success:
            # Find the generated cover
            for f in os.listdir(cover_output):
                if f.endswith(".jpg") and "_preview" not in f and f != "cover_best.jpg":
                    cover_paths.append(os.path.join(cover_output, f))
                    break

    return cover_paths


def step3_publish(post_data_path: str, cover_paths: list, cdp_endpoint: str) -> bool:
    """Step 3: Publish to Xiaohongshu."""
    with open(post_data_path, "r", encoding="utf-8") as f:
        post_data = json.load(f)

    # Get selected title and body
    selected_title = post_data.get("selected_title", "")
    if not selected_title:
        titles = post_data.get("titles", [])
        if titles:
            selected_title = titles[0].get("text", "")

    body = post_data.get("body", "")
    cta = post_data.get("cta", "")
    hashtags = post_data.get("hashtags", [])

    # Combine body + CTA + hashtags
    content = f"{body}\n\n{cta}"
    if hashtags:
        content += "\n\n" + " ".join(hashtags)

    # Use best cover or first available
    image_path = cover_paths[0] if cover_paths else None
    if not image_path:
        print("  ❌ No cover images available!")
        return False

    cmd = [
        PYTHON,
        os.path.join(SCRIPTS_DIR, "xhs_publish.py"),
        "--title", selected_title,
        "--content", content,
        "--images", image_path,
        "--cdp", cdp_endpoint,
    ]

    return run_step(
        f"Step 3: Publishing — 「{selected_title}」",
        cmd, timeout=300
    )


def main():
    parser = argparse.ArgumentParser(
        description="Xiaohongshu Auto-Publish — Full Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline from topic:
  %(prog)s --topic "蜡笔小新妈妈美伢的辛酸史"

  # With style and emoji:
  %(prog)s --topic "Topic" --style "emotional" --emoji "😭"

  # Dry run (generate content + covers, don't publish):
  %(prog)s --topic "Topic" --dry-run

  # Use existing content JSON:
  %(prog)s --from-json /tmp/xhs_post/post_data.json

  # Custom output directory:
  %(prog)s --topic "Topic" --output /tmp/my_post
        """
    )

    parser.add_argument("--topic", type=str, help="Post topic (triggers content generation)")
    parser.add_argument("--style", default="auto",
                        choices=["auto", "funny", "emotional", "inspirational", "savage", "warm"],
                        help="Content style (default: auto)")
    parser.add_argument("--emoji", default="", help="Primary emoji (e.g., 😭 🌸 🔥)")
    parser.add_argument("--output", default="/tmp/xhs_auto_post", help="Output directory")
    parser.add_argument("--from-json", type=str, help="Skip content generation, use existing post_data.json")
    parser.add_argument("--dry-run", action="store_true", help="Generate content + covers, skip publishing")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222", help="CDP endpoint URL")

    args = parser.parse_args()

    # Validate args
    if not args.topic and not args.from_json:
        parser.error("Either --topic or --from-json is required")

    print("🎯" + "=" * 58)
    print("  XIAOHONGSHU AUTO-PUBLISH — Full Pipeline")
    print("🎯" + "=" * 60)

    if args.topic:
        print(f"  📝 Topic:  {args.topic}")
        print(f"  🎨 Style:  {args.style}")
        print(f"  😀 Emoji:  {args.emoji or 'auto'}")
    if args.from_json:
        print(f"  📂 JSON:   {args.from_json}")
    print(f"  📁 Output: {args.output}")
    print(f"  🔧 Mode:   {'DRY RUN' if args.dry_run else 'FULL PUBLISH'}")

    # ── Step 1: Generate Content ──────────────────────────────────────────
    post_data_path = None
    if args.from_json:
        post_data_path = args.from_json
        if not os.path.exists(post_data_path):
            print(f"❌ JSON file not found: {post_data_path}")
            sys.exit(1)
        print(f"\n  📂 Using existing content: {post_data_path}")
    else:
        post_data_path = step1_generate_content(
            args.topic, args.style, args.emoji, args.output
        )

    # If agent processing is needed, stop here and wait
    if post_data_path is None:
        print(f"\n{'='*60}")
        print("⏸️  PAUSED — Agent processing required")
        print(f"{'='*60}")
        print(f"\n  The content generator needs LLM processing.")
        print(f"  The agent should:")
        print(f"  1. Read the prompt from the output directory")
        print(f"  2. Generate the content")
        print(f"  3. Save as post_data.json")
        print(f"  4. Re-run this script with --from-json flag")
        print(f"\n  Re-run command:")
        print(f"  $PYTHON {__file__} --from-json {os.path.join(args.output, 'content', 'post_data.json')} --output {args.output}")
        sys.exit(0)

    # ── Step 2: Generate Covers ───────────────────────────────────────────
    cover_paths = step2_generate_covers(post_data_path, args.output)
    if cover_paths:
        print(f"\n  ✅ {len(cover_paths)} cover(s) generated:")
        for p in cover_paths:
            size = os.path.getsize(p) // 1024 if os.path.exists(p) else 0
            print(f"    📄 {os.path.basename(p)} ({size}KB)")
    else:
        print("\n  ⚠️  No covers generated")

    # ── Step 3: Publish ───────────────────────────────────────────────────
    if args.dry_run:
        print(f"\n{'='*60}")
        print("🏁 DRY RUN — Skipping publish")
        print(f"{'='*60}")
        with open(post_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        title = data.get("selected_title", "N/A")
        body = data.get("body", "N/A")
        hashtags = data.get("hashtags", [])
        print(f"\n  📌 Title: {title}")
        print(f"  📝 Body: {body[:200]}...")
        print(f"  🏷️  Tags: {' '.join(hashtags)}")
        print(f"  🖼️  Covers: {len(cover_paths)}")
    else:
        success = step3_publish(post_data_path, cover_paths, args.cdp)
        if success:
            print(f"\n{'='*60}")
            print("🎉🎉🎉 AUTO-PUBLISH COMPLETE! 🎉🎉🎉")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("❌ PUBLISH FAILED")
            print(f"{'='*60}")
            sys.exit(1)


if __name__ == "__main__":
    main()
