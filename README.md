# 阿里云大模型工程师 ACA

课文抓取自 [edu.aliyun.com course 3126500](https://edu.aliyun.com/course/3126500)（快照 2026-10-28），本地整理于 2026-11-10。这是一份离线学习存档，不是课程官方发布物。账号、价格和法规会变化，使用前先看 [勘误](勘误.md)。

在线阅读：<https://www.shujukexue.com/Aliyun-ACA/>

## 怎么读

从 [index.md](index.md) 进入。11 篇课文按课时编号排列，每篇页眉有上一课、返回目录、下一课。

课程主线是：遇到一个具体任务时，按「先便宜后昂贵」选择方案。

```text
说清楚 → 补资料 → 改模型 → 让它干活 → 固化方法 → 自我检查 → 守住边界
提示词    RAG/工具   微调     Agent       Skill     自检闭环    安全合规
```

课时 01、02 讲大模型怎么工作、能做什么。课时 11 把这条线收成选型框架。

交互 SVG 在 Markdown 阅读器里通常只有静态画面，用浏览器打开 `assets/` 里的文件才能看动效。图内文字见 [图示文字索引](图示文字索引.md)。

## 目录

| 位置 | 内容 |
| --- | --- |
| `01-*.md` … `11-*.md` | 11 篇课文 |
| `index.md` | 课时目录、按问题找课时、模型与产品清单 |
| `勘误.md` | 时效性与法规复核 |
| `图示文字索引.md` | 交互 SVG 的图内文字 |
| `assets/` | 图片、视频、交互 SVG |
| `source/` | 原始 HTML 快照，用来溯源 |
| `_backup/2026-11-10/` | 本轮整理前的课文 |
| `tools/` | 整理与校验脚本 |
| `_config.yml`、`_toc.yml` | Jupyter Book 配置 |

## 本地构建

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/jupyter-book build .
```

页面在 `_build/html/`。推送到 `main` 后，GitHub Actions 会重新构建并发布到 Pages。
