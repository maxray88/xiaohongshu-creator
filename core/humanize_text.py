#!/usr/bin/env python3
"""
情绪树洞 — 文本去 AI 味（规则版，零 LLM）

对 01:00 生成的 V1 内容做口语化处理：
- 书面连接词 → 口语词
- 插入自然语气词
- 打破超长段落
- 删除结构化标记（"第一"/"第二"/"第三"）

不依赖 LLM，纯确定性规则，幂等（多次调用结果一致）。
"""
import json
import os
import re
import sys

from io_utils import atomic_write_json

# 书面 → 口语替换表
REPLACEMENTS = {
    "此外": "还有",
    "因此": "所以",
    "然而": "不过",
    "但是": "但",
    "并且": "而且",
    "或者": "要么",
    "如果": "要是",
    "虽然": "虽说",
    "即使": "就算",
    "不仅": "不光",
    "甚至": "以至于",
    "导致": "搞得",
    "产生": "冒出",
    "形成": "成了",
    "对于": "对",
    "关于": "有关",
    "通过": "靠",
    "进行": "做",
    "表示": "说",
    "认为": "觉得",
    "希望": "盼着",
    "需要": "得",
    "应该": "该",
    "可能": "也许",
    "非常": "特别",
    "十分": "挺",
    "相当": "蛮",
    "极其": "超",
    "逐渐": "慢慢",
    "突然": "忽然",
    "最终": "到头来",
    "实际上": "说实话",
    "事实上": "其实",
    "总的来说": "说到底",
    "换句话说": "说白了",
    "值得注意的是": "你发现没",
    "不可否认": "确实",
    "显而易见": "明摆着",
    "众所周知": "大家都知道",
    "综上所述": "所以啊",
    "由此可见": "你看",
    "因此可见": "所以说",
}

# 结构化标记（只删真正的「序号/列举」连接词）
#
# 这里绝不能出现 因此 / 所以 / 不过 / 然而 / 此外 / 另外 / 同时 ——
# 它们是语义连接词，删掉会改变句间逻辑。2026-09-27 实测 bug：
# REPLACEMENTS 先把「因此」换成「所以」，本表随后又把「所以」删空，
# 于是「因此，我去了。」变成「我去了。」，语义凭空消失。
# 保留的只有表示列举顺序的：首先/其次/最后/总之/综上/一方面/另一方面，
# 以及列表编号（行首序号与 (1) 这类括注）。
STRUCTURED_PATTERNS = [
    # 列表编号：锚定行首，否则「3.14」会被腰斩。
    # 顿号后允许零空格（中文习惯写「1、内容」），点号后要求空格或行尾
    #（「3.14」不能当编号）。
    r"^\s*\d+、\s*",
    r"^\s*\d+\.\s+",
    r"^\s*[\(（]\d+[\)）]\s*",
    # 括号式注号：只在纯注号形态出现时才删
    r"[\(（]\d{1,2}[\)）](?=\s|$)",
    # 顺序词必须「最长匹配优先」：一方面 是  另一方面  的子串，
    # 顺序反了会把「另一方面」切成「另」。2026-09-27 Reviewer 抓出。
    r"另一方面[,，、]?\s*",
    r"一方面[,，、]?\s*",
    r"首先[,，、]?\s*",
    r"其次[,，、]?\s*",
    r"最后[,，、]?\s*",
    r"总之[,，、]?\s*",
    # 「综上」不删：REPLACEMENTS 有「综上所述→所以啊」的正确映射，
    # 删了会先切出「所述，很好。」这种残句，正则永远吃不到映射。
]


def _strip_structured(text: str) -> str:
    """删除列举序号/编号。逐行处理，只动行首的序号标记。

    「第[一二三…]+」是正文常用表达（第一次、第二天），不能删；
    「\\d+[.、]」会腰斩小数（3.14 → 14）。故两者都不在通用路径里删，
    只有当它们位于行首且形似列表编号时才处理。
    """
    out = []
    for line in text.split("\n"):
        s = line
        # 行首「第N、」后紧跟正文时才视为列举项（"第一，" 是列举；"第一次" 不是）
        m = re.match(r"^(\s*)第[一二三四五六七八九十]+([,，、])(\s*)", s)
        if m:
            s = s[m.end():]
        out.append(s)
    return "\n".join(out)


def _collapse_adjacent_dupes(text: str) -> str:
    """合并紧邻重复的词：「还有还有」→「还有」。

    只处理完全相同、且中间没有标点/空格的相邻重复（那是替换撞词
    造成的，不是作者本意）。像「看看」「一点点」这类叠词不受影响。
    """
    # 2~4 字的中文词，重复即视为叠词噪声
    return re.sub(r"([\u4e00-\u9fa5]{2,4})\1", r"\1", text)


def humanize_text(text: str) -> str:
    """对纯文本做口语化处理。"""
    if not text:
        return text

    # 1. 先删结构化标记（必须在替换之前，否则「因此→所以」会被随后
    #    的「所以」删除规则吃掉，语义连接词凭空消失）
    for pattern in STRUCTURED_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)
    text = _strip_structured(text)

    # 2. 书面 → 口语替换
    #
    # 必须「单遍扫描」而不是逐条 str.replace：
    #   - 顺序 replace 会让前一条的替换结果被后一条再次加工
    #     （「此外」→「还有」，原文里已有「还有」就变成「还有还有」）
    #   - 还会二次替换已在原文中的同名字串（幂等性被破坏）
    # 用 re.sub 的回调形式：一次扫描，每个位置只应用一条规则（最长键优先）。
    if REPLACEMENTS:
        keys = sorted(REPLACEMENTS, key=len, reverse=True)  # 最长匹配优先
        pat = re.compile("|".join(re.escape(k) for k in keys))
        table = REPLACEMENTS
        text = pat.sub(lambda m: table[m.group(0)], text)

    # 3. 打破超长段落（每 3-4 句切一段）
    text = _break_long_paragraphs(text)

    # 3b. 合并替换产生的重复词
    # 「此外」→「还有」撞上原文已有的「还有」会得到「还有还有」。
    # 单遍替换已经保证了「不会被二次加工」，但原文里本来就有的重复
    # 仍需在这里收掉。
    text = _collapse_adjacent_dupes(text)

    # 4. 清理多余空格和标点
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"，，+", "，", text)
    text = re.sub(r"。。+", "。", text)
    text = re.sub(r"！！+", "！", text)
    text = re.sub(r"？？+", "？", text)

    return text.strip()


def _break_long_paragraphs(text: str) -> str:
    """把超长段落切成短段。"""
    paragraphs = text.split("\n")
    result = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            result.append("")
            continue

        # 按句号、问号、感叹号切分句子
        sentences = re.split(r"(?<=[。！？])", para)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 3:
            result.append(para)
        else:
            # 每 2-3 句切一段
            chunk = []
            for i, sent in enumerate(sentences):
                chunk.append(sent)
                if (i + 1) % 3 == 0:
                    result.append("".join(chunk))
                    chunk = []
            if chunk:
                result.append("".join(chunk))

    return "\n".join(result)


def humanize_html(html: str) -> str:
    """对 HTML 中的文本节点做口语化处理，保留标签结构。"""
    if not html:
        return html

    # 提取 <p>, <h1>-<h6>, <span>, <div> 等标签内的文本
    def replace_text_in_tag(match):
        tag = match.group(1)
        attrs = match.group(2) or ""
        content = match.group(3)
        # 只处理纯文本内容（不含嵌套标签）
        if "<" not in content:
            content = humanize_text(content)
        return f"<{tag}{attrs}>{content}</{tag}>"

    # 匹配常见文本标签
    html = re.sub(
        r"<(p|h[1-6]|span|div|li|td|th|a|strong|em|b|i|u)([^>]*)>([^<]*?)</\1>",
        replace_text_in_tag,
        html,
        flags=re.DOTALL,
    )

    return html


def humanize_day_dir(day_dir: str) -> dict:
    """处理整个 day 目录的 V1 内容。"""
    results = {"post_data": False, "html_cards": 0, "errors": []}

    # 1. 处理 post_data.json
    pd_path = os.path.join(day_dir, "post_data.json")
    if os.path.isfile(pd_path):
        try:
            with open(pd_path, encoding="utf-8") as f:
                pd = json.load(f)

            original_text = pd.get("content_text", "")

            # 幂等守卫：已经处理过就整体跳过。
            # 旧实现无条件用 content_text 当「原文」重跑并覆盖
            # content_text_original —— 第二次跑就把已处理文本存成"原文"，
            # 真正的原文永久丢失（2026-09-27 实测）。而且 content_text_original
            # 原本也没派上用场，01:30 之后没人读它。
            if pd.get("content_text_humanized"):
                results["post_data"] = True
                results["skipped_already_humanized"] = True
            elif original_text:
                pd["content_text_original"] = original_text
                pd["content_text"] = humanize_text(original_text)
                pd["content_text_humanized"] = True

                atomic_write_json(pd_path, pd)
                results["post_data"] = True
            else:
                with open(pd_path, "w", encoding="utf-8") as f:
                    json.dump(pd, f, ensure_ascii=False, indent=2)
                results["post_data"] = True
        except Exception as e:
            results["errors"].append(f"post_data.json: {e}")

    # 2. 处理 HTML 卡片
    img_dir = os.path.join(day_dir, "images")
    if os.path.isdir(img_dir):
        for fname in os.listdir(img_dir):
            if fname.endswith(".html"):
                fpath = os.path.join(img_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        html = f.read()

                    humanized = humanize_html(html)
                    if humanized != html:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(humanized)
                        results["html_cards"] += 1
                except Exception as e:
                    results["errors"].append(f"{fname}: {e}")

    return results


def main():
    if len(sys.argv) > 1:
        day_dir = sys.argv[1]
    else:
        # 默认找今天的 V1 目录
        base = os.path.expanduser("~/.hermes/data/xhs_treehole")
        import time
        today_c = time.strftime("%Y%m%d")
        days = sorted(
            d for d in os.listdir(base)
            if d.startswith("day_") and not d.endswith("_v2")
            and os.path.isdir(os.path.join(base, d))
        )
        day_name = next((d for d in reversed(days) if d[4:12] == today_c), None)
        if not day_name:
            print(f"❌ 今天（{today_c}）没有 V1 目录")
            sys.exit(1)
        day_dir = os.path.join(base, day_name)

    if not os.path.isdir(day_dir):
        print(f"❌ 目录不存在: {day_dir}")
        sys.exit(1)

    print(f"🧬 Humanize: {os.path.basename(day_dir)}")
    results = humanize_day_dir(day_dir)

    if results["post_data"]:
        print("  ✅ post_data.json content_text 已处理")
    if results["html_cards"] > 0:
        print(f"  ✅ {results['html_cards']} 张 HTML 卡片已处理")
    if results["errors"]:
        for e in results["errors"]:
            print(f"  ⚠️ {e}")

    print("Done")


if __name__ == "__main__":
    main()
