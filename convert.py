"""Convert the user-saved course HTML snapshots, preserving local media."""
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urlparse, unquote
import hashlib
import json
import re
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parent
TITLES = ['认识大模型', '大模型的典型应用场景', '通过优化输入来提升回答质量',
          '通过 RAG 增强大模型回答原本无法回答的问题', '通过微调改善大模型在垂直领域的表现',
          '安装桌面 Agent，开始用它干活', '让 Agent 接入知识库和工具', '用 Skill 固化你的工作方法',
          '给 Agent 加一道自检闭环', '大模型应用的安全合规', '学习总结']
manifest = []
downloads = {}
alias_file = ROOT / 'media_aliases.json'
aliases = json.loads(alias_file.read_text()) if alias_file.exists() else {}

def clean(text):
    return text.replace('\ufeff', '').replace('\u200b', '').replace('\xa0', ' ')

for num, path in enumerate(sorted((ROOT / 'source').glob('*.html')), 1):
    raw = path.read_text()
    soup = BeautifulSoup(raw, 'html.parser')
    target = soup.select_one('div.content___B0yfs div.player___xmi1j')
    assert target is not None, path
    article = target.select_one('article') or target
    source_url = re.search(r'saved from url=\(\d+\)([^\s]+)', raw)[1]
    assets = ROOT / 'assets' / path.stem
    assets.mkdir(parents=True, exist_ok=True)
    media = []

    def localize(src):
        if not src:
            return ''
        parsed = urlparse(src)
        filename = unquote(parsed.path).rsplit('/', 1)[-1]
        filename = Path(aliases.get(f'assets/{path.stem}/{filename}', filename)).name
        local = path.with_name(path.stem + '_files') / filename
        if not local.is_file():
            local = assets / filename
        if parsed.scheme not in ('http', 'https') and local.is_file():
            dest = assets / filename
            if local.resolve() != dest.resolve():
                shutil.copy2(local, dest)
            result = dest.relative_to(ROOT).as_posix()
            media.append({'source': src, 'local': result, 'status': 'saved'})
            return result
        if parsed.scheme in ('http', 'https'):
            ext = Path(parsed.path).suffix.lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.mp4', '.webm', '.mp3'):
                return src
            dest = assets / (hashlib.sha256(src.encode()).hexdigest()[:12] + ext)
            downloads[src] = dest
            result = dest.relative_to(ROOT).as_posix()
            media.append({'source': src, 'local': result, 'status': 'pending'})
            return result
        media.append({'source': src, 'status': 'unresolved'})
        return src

    for img in article.select('img'):
        img['src'] = localize(img.get('src', ''))
    for src in article.select('video[src], source[src], iframe[src]'):
        src['src'] = localize(src.get('src', ''))
    for a in article.select('a[href]'):
        if re.search(r'\.(mp4|webm|mp3|svg)(\?|$)', a['href'], re.I):
            a['href'] = localize(a['href'])

    def render(node):
        if isinstance(node, NavigableString):
            return clean(str(node))
        tag = node.name
        if tag in ('script', 'style', 'template', 'button', 'colgroup'):
            return ''
        if node.get('data-sticker') or node.get('data-cangjie-text-layer'):
            return ''
        if node.get('data-type') == 'code':
            lines = node.select('pre.CodeMirror-line')
            text = '\n'.join(clean(x.get_text()) for x in lines)
            if not lines:
                text = clean(node.get_text())
            return '\n\n```text\n' + text + '\n```\n\n'
        if tag == 'img':
            return '![' + clean(node.get('alt', '')).replace(']', '\\]') + '](' + node.get('src', '') + ')'
        if tag == 'video':
            src = node.get('src') or (node.find('source') or {}).get('src', '')
            return '\n\n[视频（本地文件）](' + src + ')\n\n' if src else ''
        if tag == 'iframe':
            src = node.get('src', '')
            return '\n\n[交互内容](' + src + ')\n\n'
        if tag == 'source':
            return ''
        if tag == 'table':
            # Fenced blocks cannot render inside a GFM table cell. Expand these
            # comparisons into labeled blocks without altering their contents.
            if node.select_one('[data-type="code"], blockquote'):
                parts = []
                rows = node.find_all('tr')
                has_headers = not rows[0].select_one('[data-type="code"], blockquote') and len(rows) > 1
                headers = [clean(c.get_text()).strip() for c in rows[0].find_all(['td', 'th'], recursive=False)] if has_headers else []
                for row in (rows[1:] if has_headers else rows):
                    for index, cell in enumerate(row.find_all(['td', 'th'], recursive=False)):
                        label = headers[index] if index < len(headers) else ''
                        parts.append(('**' + label + '**\n\n' if label else '') + ''.join(render(x) for x in cell.children).strip())
                return '\n\n' + '\n\n'.join(parts) + '\n\n'
            rows = []
            for row in node.find_all('tr', recursive=True):
                if row.find_parent('table') != node:
                    continue
                cells = []
                for cell in row.find_all(['td', 'th'], recursive=False):
                    txt = ''.join(render(x) for x in cell.children).strip()
                    txt = re.sub(r'\n{2,}', '\n\n', txt)
                    txt = txt.replace('|', '\\|').replace('\n\n', '<br><br>').replace('\n', '<br>')
                    cells.append(txt)
                rows.append(cells)
            if not rows:
                return ''
            width = max(map(len, rows))
            rows = [r + [''] * (width - len(r)) for r in rows]
            lines = ['| ' + ' | '.join(r) + ' |' for r in rows]
            lines.insert(1, '| ' + ' | '.join(['---'] * width) + ' |')
            return '\n\n' + '\n'.join(lines) + '\n\n'
        text = ''.join(render(x) for x in node.children)
        if tag == 'a':
            href = node.get('href', '')
            return '[' + (text.strip() or href) + '](' + href + ')' if href else text
        if re.fullmatch('h[1-6]', tag or ''):
            return '\n\n' + '#' * int(tag[1]) + ' ' + text.strip().replace('**', '') + '\n\n'
        if tag == 'hr':
            return '\n\n---\n\n'
        if tag == 'br':
            return '\n'
        if tag == 'blockquote':
            return '\n\n' + '\n'.join('> ' + x for x in text.strip().splitlines()) + '\n\n'
        if tag == 'code':
            return '`' + text + '`'
        if tag == 'pre':
            return '\n\n```text\n' + text + '\n```\n\n'
        if tag == 'span' and text.strip() and 'font-weight: bold' in node.get('style', ''):
            return '\n'.join('**' + line.strip() + '**' if line.strip() else '' for line in text.split('\n'))
        if tag == 'div' and node.get('data-type') == 'paragraph':
            return '\n\n' + text.strip() + '\n\n'
        return text

    body = render(article)
    body = re.sub(r'\n[ \t]+\n', '\n\n', body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    body = re.sub(r'(?m)^[➔●•]\s*\n\s*\n', '- ', body)
    # Keep source examples/code intact while normalizing prose list markers.
    chunks = re.split(r'(```[^\n]*\n.*?\n```)', body, flags=re.S)
    for index in range(0, len(chunks), 2):
        prose = chunks[index]
        prose = re.sub(r'(?m)^(> )?(\d+[.、])\s*\n(?:> ?\n|\s*\n)*(?:> )?', lambda m: (m[1] or '') + m[2].replace('、', '.') + ' ', prose)
        prose = re.sub(r'(?m)^(#{1,6} .+)\n\n---\n\n', r'\1\n\n', prose)
        chunks[index] = prose
    body = ''.join(chunks)
    filename = f'{num:02d}-{TITLES[num-1]}.md'
    (ROOT / filename).write_text(f'# 课时{num}：{TITLES[num-1]}\n\n来源：[{source_url}]({source_url})\n\n' + body + '\n')
    manifest.append({'lesson': num, 'title': TITLES[num-1], 'source': source_url,
                     'markdown': filename, 'text_characters': len(clean(article.get_text())),
                     'images': len(article.select('img')), 'media': media})

for src, dest in downloads.items():
    try:
        if not dest.exists():
            request = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=45) as response, dest.open('wb') as output:
                shutil.copyfileobj(response, output)
        assert dest.stat().st_size > 0
        print('downloaded', dest.relative_to(ROOT), dest.stat().st_size, flush=True)
    except Exception as exc:
        print('failed', src, str(exc), flush=True)
    for lesson in manifest:
        for item in lesson['media']:
            if item['source'] == src:
                item['status'] = 'saved' if dest.is_file() and dest.stat().st_size else 'failed'
                if item['status'] == 'failed':
                    md = ROOT / lesson['markdown']
                    md.write_text(md.read_text().replace(item['local'], src))

(ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
print('Converted', len(manifest), 'lessons')
