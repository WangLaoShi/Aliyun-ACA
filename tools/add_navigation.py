#!/usr/bin/env python3
"""给 11 个课时补三层东西：
1. 页眉元信息（抓取日 / 整理日 / 勘误与图示索引入口）
2. 上一页、目录、下一页导航
3. 课时11 回顾表里的课时号 → 指向本地课文
文件名含空格与中文，链接目标统一做 URL 编码。"""
import glob
import os
import re
import urllib.parse

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safewrite import save  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = "2026-10-28"
REVISED = "2026-11-10"
META = (
    f"> 存档快照：课文抓取自阿里云大模型 ACA 认证课程（course 3126500）{SNAPSHOT}，"
    f"本地整理 {REVISED}。"
    f"交互图内文字见 [图示文字索引](%E5%9B%BE%E7%A4%BA%E6%96%87%E5%AD%97%E7%B4%A2%E5%BC%95.md)，"
    f"时效性与法规复核见 [勘误](%E5%8B%98%E8%AF%AF.md)。"
)


def lessons():
    out = {}
    for p in sorted(glob.glob(os.path.join(REPO, "*.md"))):
        name = os.path.basename(p)
        m = re.match(r"^(\d{2})-(.+)\.md$", name)
        if not m:
            continue
        num = int(m.group(1))
        title = open(p, encoding="utf-8").readline().strip()
        title = re.sub(r"^#\s*课时\d+[：:]\s*", "", title)
        out[num] = (name, title)
    return out


def link(name, label):
    return f"[{label}]({urllib.parse.quote(name)})"


def main():
    ls = lessons()
    for num in sorted(ls):
        name, title = ls[num]
        path = os.path.join(REPO, name)
        text = open(path, encoding="utf-8").read()
        if "存档快照：" in text:
            print(f"{name[:24]:26} 已有元信息，跳过")
            continue
        prev_n, next_n = num - 1, num + 1
        navs = []
        if prev_n in ls:
            navs.append("← " + link(ls[prev_n][0], f"课时{prev_n} {ls[prev_n][1]}"))
        navs.append(link("index.md", "返回目录"))
        if next_n in ls:
            navs.append(link(ls[next_n][0], f"课时{next_n} {ls[next_n][1]}") + " →")
        nav = "\n\n".join(["", " ｜ ".join(navs)])
        # 插在「来源：」行之后
        text, n = re.subn(
            r"(^来源：.*\n)",
            r"\1" + "\n" + META + nav + "\n",
            text,
            count=1,
            flags=re.M,
        )
        if n == 0:
            raise SystemExit(f"{name} 没找到「来源：」行，请人工处理")
        if num == 11:
            text = link_review_table(text, ls)
        save(path, text)
        print(f"{name[:24]:26} 元信息+导航 已加")


def link_review_table(text, ls):
    """课时11 回顾表第一列：课时N → 可点击。"""

    def rep(m):
        n = int(m.group(1))
        if n not in ls:
            return m.group(0)
        return f"| {link(ls[n][0], m.group(0).strip('| ').strip())} |"

    return re.sub(r"\|\s*(课时(\d{1,2})[^|]*?)\s*\|", rep, text)


if __name__ == "__main__":
    main()
