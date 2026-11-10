#!/usr/bin/env python3
"""P0 收尾：修抓取残留的符号与排版，不改任何一个字。

- 04 里 6 个孤行「○」→ 归位成二级列表
- 「复****（」这类断裂加粗（跳过 138****5678 这种手机号掩码）
- 方向写反的引号 ”xxx” → “xxx”
- 中文与英文之间补空格（跳过代码块、链接目标、表格）
- 行尾空格、连续空行
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402

CJK = r"[\u4e00-\u9fff]"
ORPHAN = re.compile(r"^\s*([○●▪•‣])\s*$")
def fix_quotes(text):
    """块内交替配对：处在「未开启」状态时遇到的 ”，就是写反了的左引号。
    这样 `。”` 这类合法闭引号不会被误改。
    提示词代码块里也是中文弯引号（不是代码语义），同样照改。"""
    out, flips = [], 0
    opened = False
    for line in text.split("\n"):
        if not line.strip():
            opened = False  # 空行重置配对状态
            out.append(line)
            continue
        buf = []
        for ch in line:
            if ch == "“":
                opened = True
            elif ch == "”":
                if opened:
                    opened = False
                else:
                    ch = "“"
                    opened = True  # 翻转后它就是开引号，否则后面的闭引号会跟着被误翻
                    flips += 1
            buf.append(ch)
        out.append("".join(buf))
    return "\n".join(out), flips


def nest_bullets(text):
    lines = text.split("\n")
    out, n = [], 0
    for i, line in enumerate(lines):
        m = ORPHAN.match(line)
        if m:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                prev = next((l for l in reversed(out) if l.strip()), "")
                indent = "  " if prev.lstrip().startswith("- ") else ""
                out.append(f"{indent}- {lines[j].strip()}")
                out.append("")
                n += 1
                continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)), n


def split_out_urls(line):
    """把链接/图片的 URL 部分保护起来，只处理可见文字。"""
    parts = []
    last = 0
    for m in re.finditer(r"!?\[[^\]]*\]\([^)]*\)", line):
        parts.append(("text", line[last : m.start()]))
        parts.append(("url", m.group(0)))
        last = m.end()
    parts.append(("text", line[last:]))
    return parts


def spacing(text):
    lines = text.split("\n")
    fence = False
    total = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence or not line.strip() or line.strip().startswith("|"):
            continue
        rebuilt, cnt = [], 0
        for kind, seg in split_out_urls(line):
            if kind == "url":
                rebuilt.append(seg)
                continue
            seg, c1 = re.subn(rf"({CJK})(?=[A-Za-z])", r"\1 ", seg)
            seg, c2 = re.subn(rf"(?<=[A-Za-z])({CJK})", r" \1", seg)
            rebuilt.append(seg)
            cnt += c1 + c2
        if cnt:
            lines[i] = "".join(rebuilt)
            total += cnt
    return "\n".join(lines), total


def main():
    for path in sorted(glob.glob(os.path.join(ROOT, "*.md"))):
        name = os.path.basename(path)
        t = open(path, encoding="utf-8").read()
        t, nb = nest_bullets(t)
        t, ng = re.subn(r"(?<!\d)\*\*\*\*(?!\d)", "", t)
        t, nq = fix_quotes(t)
        t, ns = spacing(t)
        t = re.sub(r"[ \t]+$", "", t, flags=re.M)
        t = re.sub(r"\n{3,}", "\n\n", t)
        save(path, t)
        bal = t.count("“") - t.count("”")
        print(
            f"{name[:26]:28} 嵌套={nb} 断粗体={ng} 反引号={nq} 补空格={ns:>3} 引号差={bal}"
        )


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    main()
