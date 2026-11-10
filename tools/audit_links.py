#!/usr/bin/env python3
"""链接体检：本地路径是否真的存在（含 %20 解码），http 链接是否有明显畸形。
不改文件，只报告。"""
import glob
import os
import re
import sys
import urllib.parse

REPO = os.environ.get("MD_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSELESSON = re.compile(r"edu\.aliyun\.com/course/\d+/lesson/(?!$)[^\"'\s)]*")

total_local = total_http = 0
missing, malformed = [], []

for p in sorted(glob.glob(os.path.join(REPO, "*.md"))):
    base = os.path.dirname(p)
    name = os.path.basename(p)
    text = open(p, encoding="utf-8").read()
    for m in re.finditer(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)", text):
        url = m.group(1)
        lineno = text[: m.start()].count("\n") + 1
        if re.match(r"^https?://", url):
            total_http += 1
            seg = COURSELESSON.search(url)
            if seg and not re.fullmatch(r"\d+", seg.group(0).rsplit("/", 1)[1]):
                malformed.append(f"{name}:{lineno} {url}")
        elif url.startswith("#"):
            continue
        else:
            total_local += 1
            target = os.path.normpath(os.path.join(base, urllib.parse.unquote(url.split("#")[0])))
            if not os.path.exists(target):
                missing.append(f"{name}:{lineno} {url}")

    # 正文里裸露的 markdown 链接（不在 []() 里的）也顺手看畸形模式
    for m in re.finditer(COURSELESSON, text):
        u = m.group(0)
        if not re.fullmatch(r"\d+", u.rsplit("/", 1)[1]) and u not in [x.split(" ", 1)[1] for x in malformed]:
            malformed.append(f"{name}:{text[: m.start()].count(chr(10)) + 1} (裸链) {u}")

print(f"本地链接 {total_local} 条，缺失 {len(missing)}")
for x in missing:
    print("  ✗", x)
print(f"http 链接 {total_http} 条，课程页链接畸形 {len(set(malformed))}")
for x in sorted(set(malformed)):
    print("  ✗", x)
sys.exit(1 if missing or malformed else 0)
