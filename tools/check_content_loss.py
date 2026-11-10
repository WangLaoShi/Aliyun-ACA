#!/usr/bin/env python3
"""句子级内容不丢失校验：把 markdown 归一化成「实质文字 + 链接/图片路径」集合，
再检查备份里的每一句是否仍能在当前文件里找到。新增允许，丢失即失败。

用法:
    python3 tools/check_content_loss.py            # 校验全部
    python3 tools/check_content_loss.py 03 04      # 只校验指定课时
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(ROOT, "_backup", "2026-11-10")

# 装饰性内容：有意删除或改写，不计入丢失
IGNORE_PATH_RE = re.compile(r"TB1roWqp")
# 抓取残留的垃圾 alt（尺寸后缀、占位词），逐条留档在 alt_audit.txt 里人工核对
KNOWN_JUNK = {"-c600", "image", "img", "png", "gif"}
# 有意改写、由 alt_audit.txt 单独留档核对
DECOR_CHARS = "‒▪·•"
EMOJI = "🚄✏️✅❓🧩⚠️▶️💡🎯📌🔍🧠🛠️✨🚀"


def strip_syntax(text: str) -> str:
    # <br> 是换行语义，必须当成句子边界，否则「同一行」与「拆成两行」会被误判成内容变化
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(?:center|span|div|b|i|u|font)[^>]*>", " ", text, flags=re.I)
    # 先脱掉加粗/代码标记，再补中英文空格：否则 `用**Agent**编排` 这类写法会因星号挡住
    # 而生成「用Agent编排」这种和排版无关的假句子
    text = re.sub(r"[*_`]+", "", text)
    for ch in DECOR_CHARS + EMOJI:
        text = text.replace(ch, "")
    # 中英文边界统一补一个空格，这样「排版性加空格」不会被当成内容变化
    text = re.sub(r"([\u4e00-\u9fff])(?=[A-Za-z])", r"\1 ", text)
    text = re.sub(r"([A-Za-z])(?=[\u4e00-\u9fff])", r"\1 ", text)
    return text


def units(md: str):
    """把 markdown 拆成可比较的语义单元：正文句子 + 链接目标 + 图片路径。"""
    md = strip_syntax(md)
    out = set()

    # 先摘出链接与图片，保住 URL / 本地路径这类硬内容
    for m in re.finditer(r"(!?)\[([^\]]*)\]\(([^)]+)\)", md):
        is_img, label, path = m.group(1) == "!", m.group(2), m.group(3).split()[0]
        if not IGNORE_PATH_RE.search(path):
            out.add(("link", path))
        # 图片挪到独立一行，alt 属于呈现元数据（改写它由 alt_audit.txt 核对）；
        # 普通链接的锚文本是正文，必须留在比对里
        md = md.replace(m.group(0), "\n" if is_img else "\n" + label + "\n")

    body = []
    for line in md.split("\n"):
        s = line.strip()
        if re.fullmatch(r"[-|:=\s]+", s):  # 分隔行、水平线不算内容
            continue
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^>\s*", "", s)
        s = re.sub(r"^[-*+]\s+", "", s)
        s = re.sub(r"^\d{1,2}[.)]\s+", "", s)
        s = s.replace("|", " ")
        s = re.sub(r"[*_`]+", "", s)
        if s.strip():
            body.append(s)
    joined = "\n".join(body)
    # 空白和标点都算句子边界：这样纯粹的「加/删空格」这类排版变化不会被误判成丢内容
    for sent in re.split(r"[\s，。；：？！,.;:?!“”\"'（）()\[\]、]+", joined):
        if len(sent) >= 4:
            out.add(("text", sent))
    return out


def main():
    args = sys.argv[1:]
    cur_dir = ROOT
    if args[:1] == ["--dir"]:
        cur_dir = args[1]
        args = args[2:]
    only = args
    bad = 0
    for bf in sorted(glob.glob(os.path.join(BACKUP, "*.md"))):
        name = os.path.basename(bf)
        if only and not any(name.startswith(p) for p in only):
            continue
        cur = os.path.join(cur_dir, name)
        before = units(open(bf, encoding="utf-8").read())
        after = units(open(cur, encoding="utf-8").read())
        after_text = " ".join(v for k, v in after if k == "text")
        after_links = {v for k, v in after if k == "link"}
        missing = [
            v
            for k, v in sorted(before)
            if v not in KNOWN_JUNK
            and ((k == "text" and v not in after_text) or (k == "link" and v not in after_links))
        ]
        junk = sum(1 for k, v in before if v in KNOWN_JUNK)
        if junk:
            print(f"  ({name[:16]} 跳过 {junk} 个已知抓取垃圾词)")
        if missing:
            bad += 1
            print(f"✗ {name} 丢失 {len(missing)} 个语义单元：")
            for v in missing[:15]:
                print(f"    · {v[:70]}")
            if len(missing) > 15:
                print(f"    … 另有 {len(missing) - 15} 条")
        else:
            print(f"✓ {name} 内容完整（比对单元 {len(before)}）")
    print("\n结果：", "全部通过，无内容丢失" if bad == 0 else f"{bad} 个文件存在内容丢失")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
