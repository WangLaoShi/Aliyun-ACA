#!/usr/bin/env python3
"""把课文里引用的 SVG 交互图内的文字全部抄出来，生成可检索的索引。
网页里这些图只能靠浏览器打开才能看到内容，本地 Markdown 阅读器只显示静态画面，
图内的定义、流程、数字在正文里没有对应文字。本索引不改动课文正文。"""
import datetime
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = re.compile(r"!\[[^\]]*\]\((assets/\d{2}/[^)\s]+\.svg)\)")
CAPTION = re.compile(r"^\*(图\s*\d+\s*[：:](.+?))\*$|^(图\s*\d+\s*[：:](.+))$")


def svg_labels(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    seen = []
    for n in re.findall(r"<(?:text|tspan)[^>]*>(.*?)</(?:text|tspan)>", raw, re.S):
        s = re.sub(r"<[^>]+>", "", n)
        s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        s = re.sub(r"\s+", "", s)
        if len(s) >= 2 and s not in seen:
            seen.append(s)
    return seen


def main():
    today = datetime.date.today().isoformat()
    out = [
        f"# 图示文字索引\n",
        f"生成时间：{today}　来源：11 个课时正文里引用的 SVG 交互图\n",
        "> 网页版这些图是可交互的，本地 Markdown 只能看到静态画面，"
        "图里的定义、流程和数字在正文中往往没有对应文字。"
        "本索引把每张 SVG 内的文字节点原样抄出来，方便检索、复制和朗读；"
        "课文正文未做任何改动。**结论仍以图为准。**\n",
    ]
    total_imgs = total_labels = missing = 0
    stats = []
    for md in sorted(glob.glob(os.path.join(ROOT, "*.md"))):
        name = os.path.basename(md)
        if not re.match(r"\d{2}-", name):
            continue
        text = open(md, encoding="utf-8").read()
        lines = text.split("\n")
        refs, seen = [], set()
        for i, line in enumerate(lines):
            for m in IMG.finditer(line):
                rel = m.group(1)
                if rel in seen:
                    continue
                seen.add(rel)
                cap = ""
                for j in (i + 1, i + 2, i - 1):
                    if 0 <= j < len(lines):
                        cm = CAPTION.match(lines[j].strip())
                        if cm:
                            cap = cm.group(1)
                            break
                refs.append((i + 1, rel, cap))
        if not refs:
            continue
        out.append(f"\n## {name}\n")
        n_lab = n_miss = 0
        for lineno, rel, cap in refs:
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            labels = svg_labels(path)
            n_lab += len(labels)
            body_only = [s for s in labels if s.strip("（）") and s[:6] not in text]
            n_miss += len(body_only)
            out.append(f"\n### {rel}（正文第 {lineno} 行）\n")
            if cap:
                out.append(f"图注：{cap}\n")
            if labels:
                out.append("图内文字：" + " ｜ ".join(labels) + "\n")
            if body_only:
                out.append(
                    f"\n其中正文没有写到的 {len(body_only)} 条："
                    + " ｜ ".join(body_only)
                    + "\n"
                )
            else:
                out.append("\n（图内信息正文均已覆盖）\n")
        total_imgs += len(refs)
        total_labels += n_lab
        missing += n_miss
        stats.append((name, len(refs), n_lab, n_miss))
    out.append(
        f"\n---\n\n合计 {total_imgs} 张 SVG、{total_labels} 条图内文字，"
        f"其中 {missing} 条在正文里找不到对应文字。\n"
    )
    for name, a, b, c in stats:
        out.append(f"- {name}：SVG {a} 张，图内文字 {b} 条，正文未覆盖 {c} 条")
    dest = os.path.join(ROOT, "图示文字索引.md")
    open(dest, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"已生成 {dest}")
    print(f"SVG {total_imgs} 张 · 图内文字 {total_labels} 条 · 正文未覆盖 {missing} 条")
    for name, a, b, c in stats:
        print(f"  {name[:26]:28} SVG={a:>2} 文字={b:>3} 未覆盖={c:>3}")


if __name__ == "__main__":
    main()
