#!/usr/bin/env python3
"""补写图片 alt。规则按可信度从高到低，绝不编造图形内容：
1. 图片下方/上方已有 *图N：xxx* 图注 → 直接复用图注（这是课文原有文字）
2. SVG → 取图内真实文字节点（前 3 条）作为说明
3. 其余（截图/示意图）→ 标注所属小节，形如「课时4「RAG 的实现原理」配图 2」
所有 old→new 逐条写入 alt_audit.txt 供人工核对。"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("MD_ROOT") or REPO  # md 所在目录（试跑时可指向临时副本）
IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?: \"[^\"]*\")?\)")
SIZE_SUFFIX = re.compile(r"-c\d{3}$")


def is_junk(alt: str) -> bool:
    a = SIZE_SUFFIX.sub("", alt.strip())
    return (
        not a
        or a.lower() in {"image", "img", "图片", "screenshot"}
        or bool(re.search(r"\.(svg|png|jpe?g|gif)$", a, re.I))
        or bool(re.fullmatch(r"[A-Za-z0-9_\-!]{12,}", a))
    )


def svg_labels(path: str):
    try:
        raw = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    nodes = re.findall(r"<(?:text|tspan)[^>]*>(.*?)</(?:text|tspan)>", raw, re.S)
    seen, out = set(), []
    for n in nodes:
        s = re.sub(r"<[^>]+>", "", n)
        s = (
            s.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .strip()
        )
        s = re.sub(r"\s+", "", s)
        if len(s) >= 2 and s not in seen:
            seen.add(s)
            out.append(s)
    return out[:3]


def nearby_caption(lines, idx):
    """找紧邻的图注行（*图N：xxx*），课文自带。"""
    for j in (idx + 1, idx + 2, idx - 1, idx - 2):
        if 0 <= j < len(lines):
            m = re.fullmatch(r"\*(图\s*\d+\s*[：:].+?)\*", lines[j].strip())
            if m:
                return m.group(1).strip()
    return ""


def current_section(lines, idx):
    for j in range(idx, -1, -1):
        m = re.match(r"^(#{2,4})\s+(?:\d+(?:\.\d+)*\s+)?(.+)$", lines[j])
        if m:
            return m.group(2).strip()
    return ""


def clean_alt(s: str) -> str:
    """alt 会被塞进 ![...](...) 里，绝不能带方括号，否则图片语法被撑破。"""
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)  # 链接只留锚文本
    s = re.sub(r"https?://\S+", "", s)
    s = s.replace("[", "").replace("]", "").replace("(", "（").replace(")", "）")
    s = re.sub(r"\s+", " ", s).strip(" —－·:：")
    return s


def main():
    audit = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.md"))):
        name = os.path.basename(path)
        lesson = name[:2]
        text = open(path, encoding="utf-8").read()
        lines = text.split("\n")
        counters = {}
        changed = 0
        fence = False
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                fence = not fence
                continue
            if fence or "![" not in line:
                continue
            m = IMG.search(line)
            if not m or not is_junk(m.group(1)):
                continue
            rel = m.group(2)
            ext = rel.rsplit(".", 1)[-1].lower()
            alt = nearby_caption(lines, i)
            media = os.path.join(REPO, rel)
            if not alt and ext == "svg" and os.path.exists(media):
                labels = svg_labels(media)
                alt = "SVG 图示：" + " / ".join(labels) if labels else ""
            if not alt:
                sec = clean_alt(current_section(lines, i) or name[3:-3].split("：")[-1])
                counters[sec] = counters.get(sec, 0) + 1
                alt = f"课时{int(lesson)}「{sec}」配图 {counters[sec]}"
            alt = clean_alt(alt)[:110]
            old = m.group(1)
            lines[i] = line.replace(m.group(0), f"![{alt}]({rel})")
            audit.append(f"{name} L{i+1}\told={old!r}\tnew={alt!r}")
            changed += 1
        save(path, "\n".join(lines))
        print(f"{name[:26]:28} 补写 alt={changed}")
    with open(os.path.join(ROOT, "alt_audit.txt"), "w", encoding="utf-8") as fh:
        fh.write("图片 alt 改写清单（原 alt 均为空或抓取残渣，正文文字未改动）\n")
        fh.write("\n".join(audit) + "\n")
    print(f"alt 改写清单：{len(audit)} 条 → alt_audit.txt")


if __name__ == "__main__":
    main()
