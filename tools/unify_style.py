#!/usr/bin/env python3
"""体例统一：标题层级、章节名、编号格式、emoji、图注样式、缺失空行。
只动符号，不动正文文字。"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI_PREFIX = re.compile(r"^(#{1,6}\s*)(?:[\U0001F300-\U0001FAFF✅❓✏️🚄🧩⚠️\U0001F100-\U0001F9FF]\ufe0f?\s*)+")
CAPTION = re.compile(r"^(图\s*\d+\s*[：:].+)$")
# 章节名不做改名：「学习目标」与「课程目标」是同义的正文文字，改名等于改内容
RENAME: dict[str, str] = {}


def iter_lines(text):
    """产出 (行号, 是否在代码块外, 行)。"""
    fence = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
            yield line, False
            continue
        yield line, not fence


def demote_05(text):
    """课时5 整篇比其它课高一级：除首行标题外，# → ##，## → ###，### → ####。"""
    out = []
    for idx, (line, outside) in enumerate(iter_lines(text)):
        if outside and idx > 0 and re.match(r"^#{1,5}\s", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def normalize_headings(text):
    out = []
    for line, outside in iter_lines(text):
        if outside and line.startswith("#"):
            line = EMOJI_PREFIX.sub(r"\1", line)
            m = re.match(r"^(#{1,6})\s+(\d+)\.\s+(.*)$", line)
            if m:  # 「1. 标题」→「1 标题」，与多数课一致
                line = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            m = re.match(r"^(#{1,6})\s+(\S+)\s*$", line)
            if m and m.group(2) in RENAME:
                line = f"{m.group(1)} {RENAME[m.group(2)]}"
            line = re.sub(r"\s+$", "", line)
        out.append(line)
    return "\n".join(out)


def style_captions(text):
    out = []
    prev_blank = True
    for line, outside in iter_lines(text):
        s = line.rstrip()
        if outside and prev_blank and CAPTION.match(s.strip()):
            s = f"*{s.strip()}*"
        out.append(s)
        prev_blank = not s.strip()
    return "\n".join(out)


def unglue_images(text):
    """图片独占一行、下一行却直接接正文 → 补空行。"""
    lines = text.split("\n")
    out, fence = [], False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
        out.append(line)
        if (
            not fence
            and re.fullmatch(r"\s*!\[[^\]]*\]\([^)]+\)\s*", line)
            and i + 1 < len(lines)
            and lines[i + 1].strip()
            and not lines[i + 1].lstrip().startswith(("#", "!", "*", "-", ">", "|", "<"))
        ):
            out.append("")
    return "\n".join(out)


def main():
    for path in sorted(glob.glob(os.path.join(ROOT, "*.md"))):
        name = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        if name.startswith("05"):
            text = demote_05(text)
        text = normalize_headings(text)
        text = style_captions(text)
        text = unglue_images(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        save(path, text)
        hs = [l for l in text.split("\n") if re.match(r"^#{1,4}\s", l)]
        h1 = sum(1 for l in hs if l.startswith("# "))
        emo = sum(1 for l in hs if re.search(r"[\U0001F300-\U0001FAFF✅❓✏️]", l))
        print(f"{name[:26]:28} H1={h1} 标题={len(hs)} 残留emoji标题={emo}")


if __name__ == "__main__":
    main()
