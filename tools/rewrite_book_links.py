"""把构建结果里指向 .md 的站内链接改成 Jupyter Book 的 .html 页面。"""

from pathlib import Path
from urllib.parse import unquote, urlparse
import re

ROOT = Path(__file__).resolve().parents[1]
HTML_ROOT = ROOT / "_build" / "html"
HREF_RE = re.compile(r'href="([^"]+)"')


def page_names(root: Path) -> set[str]:
    return {path.stem for path in root.glob("*.html")}


def rewrite_href(href: str, pages: set[str]) -> str:
    if href.startswith(("#", "mailto:", "javascript:")):
        return href
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"}:
        return href
    path = unquote(parsed.path)
    if not path.endswith(".md"):
        return href
    # 只改写同目录下的课文链接，保留 _sources 里的 Markdown 源文件。
    if Path(path).parent not in {Path("."), Path("")}:
        return href
    stem = Path(path).name[: -len(".md")]
    if stem not in pages:
        return href
    suffix = Path(path).with_suffix(".html").as_posix()
    if parsed.query:
        suffix += "?" + parsed.query
    if parsed.fragment:
        suffix += "#" + parsed.fragment
    return suffix


def rewrite_file(path: Path, pages: set[str]) -> int:
    text = path.read_text(encoding="utf-8")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        updated = rewrite_href(match.group(1), pages)
        if updated == match.group(1):
            return match.group(0)
        count += 1
        return f'href="{updated}"'

    updated = HREF_RE.sub(replace, text)
    if count:
        path.write_text(updated, encoding="utf-8")
    return count


def main() -> None:
    if not HTML_ROOT.is_dir():
        raise SystemExit(f"找不到构建目录：{HTML_ROOT}")
    pages = page_names(HTML_ROOT)
    changed_files = 0
    changed_links = 0
    for path in HTML_ROOT.rglob("*.html"):
        count = rewrite_file(path, pages)
        if count:
            changed_files += 1
            changed_links += count
    print(f"改写 {changed_links} 条 .md 链接，涉及 {changed_files} 个页面")


if __name__ == "__main__":
    main()
