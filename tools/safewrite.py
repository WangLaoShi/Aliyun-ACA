#!/usr/bin/env python3
"""所有改写脚本的统一出口：写盘前做长度护栏，防止误清空或大幅缩水。"""
import os


def save(path: str, text: str, min_ratio: float = 0.85) -> None:
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if old and len(text) < len(old) * min_ratio:
        raise SystemExit(
            f"拒绝写入 {path}：长度 {len(old)} → {len(text)}，"
            f"低于安全比例 {min_ratio}。请确认不是丢内容。"
        )
    if not text.strip():
        raise SystemExit(f"拒绝写入 {path}：内容为空")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
