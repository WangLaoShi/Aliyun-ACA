#!/usr/bin/env python3
"""P0 修复：只改排版符号，不动任何一个汉字。

1. 裸「‒」列表符 → `-` 列表项
2. 被拆成两行的「**1.** / **标题**」步骤 → 合并成 **1. 标题**
3. 55+4 处 490B 下载按钮装饰图标 → 删引用（文件保留），并救回被它吞掉的步骤序号
4. 视频用图片语法 → 统一成可点击链接
5. 课时1 测验答案 → 折叠，避免自测时先看到答案
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402

ICON = re.compile(r"!\[[^\]]*\]\([^)]*TB1roWqp[^)]*\)")
BARE_DASH = re.compile(r"^‒\s*$")
NUM_ONLY = re.compile(r"^\*\*\d{1,2}\.\*\*$|^(\d{1,2})\.$")
STEP_BOLD = re.compile(r"^\*\*(\d{1,2})\.\*\*$")
TITLE_BOLD = re.compile(r"^\*\*(.+)\*\*$")


def fix_bullets(text):
    """‒ 独占一行 + 空行 + 正文 → 合并为 - 列表项。"""
    lines = text.split("\n")
    out, i, n = [], 0, 0
    while i < len(lines):
        if BARE_DASH.match(lines[i].strip()):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                out.append(f"- {lines[j].strip()}")
                out.append("")
                n += 1
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), n


def merge_steps(text):
    """**1.** 与 **数据准备** 分两行 → **1. 数据准备**。"""
    lines = text.split("\n")
    out, i, n = [], 0, 0
    while i < len(lines):
        s = lines[i].strip()
        m = STEP_BOLD.match(s)
        if m:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                t = TITLE_BOLD.match(lines[j].strip())
                if t:
                    out.append(f"**{m.group(1)}. {t.group(1)}**")
                    out.append("")
                    n += 1
                    i = j + 1
                    continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), n


def drop_icons(text):
    """删装饰图标；若序号被图标吞在一行，把它接回下一句。"""
    lines = text.split("\n")
    out, i, dropped, revived = [], 0, 0, 0
    while i < len(lines):
        line = lines[i]
        if ICON.search(line):
            rest = ICON.sub("", line).strip()
            dropped += len(ICON.findall(line))
            if not rest:
                i += 1
                continue
            if NUM_ONLY.match(rest):  # 只剩 "4." 或 "**2.**"
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    num = re.search(r"\d{1,2}", rest).group(0)
                    out.append(f"{num}. {lines[j].strip()}")
                    out.append("")
                    revived += 1
                    i = j + 1
                    continue
            out.append(rest)
            i += 1
            continue
        out.append(line)
        i += 1
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return text, dropped, revived


def fix_video(text):
    def rep(m):
        return f"[▶ 视频（本地文件）]({m.group(1)})"

    text, n = re.subn(r"!\[[^\]]*\]\((assets/[^)]+\.mp4)\)", rep, text)
    text, n2 = re.subn(r"\[[^\]]*\]\((assets/[^)]+\.mp4)\)", rep, text)
    return text, n + n2


def fold_answers(text):
    """把题干下面紧跟的「正确答案 + 解析」引用块折进 details。"""
    lines = text.split("\n")
    out, i, n = [], 0, 0
    while i < len(lines):
        if lines[i].strip().startswith("> **正确答案"):
            block = []
            j = i
            while j < len(lines) and (lines[j].startswith(">") or not lines[j].strip()):
                if not lines[j].strip() and (j + 1 >= len(lines) or not lines[j + 1].startswith(">")):
                    break
                block.append(lines[j])
                j += 1
            out.append("<details>")
            out.append("")
            out.append("<summary>查看答案与解析</summary>")
            out.append("")
            out.extend(block)
            out.append("")
            out.append("</details>")
            out.append("")
            n += 1
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), n


def main():
    for path in sorted(glob.glob(os.path.join(ROOT_DIR, "*.md"))):
        name = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        text, nb = fix_bullets(text)
        text, ns = merge_steps(text)
        text, nd, nr = drop_icons(text)
        nv = 0
        if "mp4" in text:
            text, nv = fix_video(text)
        na = 0
        if "正确答案" in text:
            text, na = fold_answers(text)
        save(path, text)
        print(f"{name[:26]:28} ‒列表={nb:>2} 步骤合并={ns:>2} 去图标={nd:>2}(救回序号{nr}) 视频={nv} 答案折叠={na}")


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    main()
