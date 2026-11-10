#!/usr/bin/env python3
"""把「伪表格」还原成可读结构，不删改任何文字，只换排版符号。

网页里的提示框/对照框被抓成了只有一行表头、没有数据行的表格：
- 单列 → 说明框（扩展阅读、注意事项）：转成引用块
- 多列且单元格超长 → 真对照表：每列转成小标题 + 逐条要点
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402


def cells(line: str):
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


def fragments(cell: str):
    """按 <br> 拆单元格，逐段返回原文（不合并、不截断）。"""
    return [p.strip() for p in re.split(r"<br\s*/?>", cell) if p.strip()]


def is_pseudo_table(header_cells, nrows):
    return nrows == 0 and max((len(c) for c in header_cells), default=0) >= 80


def as_quote(frags):
    out = []
    for i, f in enumerate(frags):
        if i:
            out.append(">")
        out.append(f"> {f}")
    return "\n".join(out) + "\n"


def as_columns(frags_per_col):
    out = []
    for frags in frags_per_col:
        title = frags[0]
        if not title.startswith("**"):
            title = f"**{title}**"
        out.append(title)
        out.append("")
        for f in frags[1:]:
            out.append(f if f.startswith("!") else f"- {f}")
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def transform(text: str, path: str):
    lines = text.split("\n")
    out, i, n = [], 0, 0
    while i < len(lines):
        s = lines[i].strip()
        sep = i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip())
        if s.startswith("|") and sep:
            hc = cells(s)
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            nrows = j - i - 2
            if is_pseudo_table(hc, nrows):
                per_col = [fragments(c) for c in hc]
                out.append(as_quote(per_col[0]) if len(hc) == 1 else as_columns(per_col))
                out.append("")
                n += 1
                i = j
                continue
        out.append(lines[i])
        i += 1
    print(f"  {path[:20]} 还原伪表格 {n} 个")
    return "\n".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        text = open(p, encoding="utf-8").read()
        save(p, transform(text, p))
