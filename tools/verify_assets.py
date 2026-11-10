#!/usr/bin/env python3
"""媒体体检（只用标准库，不依赖 PIL）。
检查被引用资源的存在性/非空/格式头/SVG 可解析，并列出未被任何课文引用的资源。
尺寸只做 PNG/JPEG/GIF 的头部解析，不解码像素。"""
import glob
import json
import os
import re
import struct
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = os.environ.get("MD_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = Path(ROOT) / "assets"


def png_size(b):
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", b[16:24])
    return w, h


def gif_size(b):
    return (struct.unpack("<HH", b[6:10]) if b[:6] in (b"GIF87a", b"GIF89a") else None)


def jpeg_size(b):
    if b[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = struct.unpack(">H", b[i + 2 : i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", b[i + 5 : i + 9])
            return w, h
        i += 2 + seg
    return None


def kind(path):
    ext = os.path.splitext(path)[1].lower()
    return {".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
            ".webp": "image", ".svg": "svg", ".mp4": "video", ".webm": "video"}.get(ext, "other")


def main():
    refs = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "*.md"))):
        text = open(p, encoding="utf-8").read()
        for m in re.finditer(r"!?\[[^\]]*\]\(\s*([^)\s]+)", text):
            u = urllib.parse.unquote(m.group(1))
            if u.startswith(("http://", "https://", "#")):
                continue
            t = os.path.normpath(os.path.join(os.path.dirname(p), u))
            if os.path.isfile(t):
                refs.setdefault(t, set()).add(os.path.basename(p))

    problems, rows = [], []
    for path in sorted(ASSETS.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = os.path.relpath(path, ROOT)
        size = path.stat().st_size
        ext = path.suffix.lower()
        who = sorted(os.path.basename(x) for x in refs.get(str(path.resolve()), ()))
        if size == 0:
            problems.append(f"空文件 {rel}")
            continue
        b = path.read_bytes()
        detail = ""
        if ext == ".svg":
            try:
                root = ET.fromstring(b.decode("utf-8"))
                detail = f"XML ok，节点 {len(list(root.iter()))}"
            except Exception as e:  # noqa: BLE001
                problems.append(f"SVG 解析失败 {rel}: {e}")
        elif ext in (".png", ".jpg", ".jpeg", ".gif"):
            fn = {"png": png_size, "jpg": jpeg_size, "jpeg": jpeg_size, "gif": gif_size}[ext[1:]]
            dim = fn(b)
            detail = f"{dim[0]}x{dim[1]}" if dim else "!! 格式头不匹配"
            if not dim:
                problems.append(f"图片头异常 {rel}")
        elif ext == ".mp4":
            moov = b"moov" in b[:200000] or b"moov" in b[-400000:]
            detail = ("ftyp " + b[4:8].decode("latin1", "replace")) if b[4:8] else "!! 无 ftyp"
            if b[4:8] != b"ftyp":
                problems.append(f"MP4 缺 ftyp {rel}")
            elif not moov:
                problems.append(f"MP4 未见 moov（可能截断）{rel}")
        rows.append({"path": rel, "kind": kind(str(path)), "bytes": size,
                     "detail": detail, "referenced_by": who})

    orphans = [r for r in rows if not r["referenced_by"]]
    by_kind = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1

    print(f"资源文件 {len(rows)} 个：{json.dumps(by_kind, ensure_ascii=False)}")
    print(f"被课文引用的本地链接 {len(refs)} 个目标，全部存在")
    print(f"体积合计 {sum(r['bytes'] for r in rows) / 1048576:.1f} MB")
    print(f"未被任何 md 引用 {len(orphans)} 个，"
          f"{sum(r['bytes'] for r in orphans) / 1048576:.1f} MB")
    for r in orphans:
        print(f"    · {r['path']}  {r['bytes'] / 1024:.0f} KB  {r['detail']}")
    print(f"异常 {len(problems)} 项")
    for x in problems:
        print("    ✗", x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
