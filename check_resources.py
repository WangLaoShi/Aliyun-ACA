"""Validate local media and Markdown links without changing course content."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote, urlparse
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
results = []
errors = []
for path in sorted((root / 'assets').rglob('*')):
    if not path.is_file():
        continue
    result = {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size}
    try:
        assert result['bytes'] > 0, 'empty file'
        if path.suffix == '.mp4':
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                    'format=duration:stream=codec_type,codec_name,width,height',
                                    '-of', 'json', str(path)], capture_output=True, text=True, check=True)
            metadata = json.loads(probe.stdout)
            assert float(metadata['format']['duration']) > 0
            assert any(s['codec_type'] == 'video' for s in metadata['streams'])
            result.update(kind='video', metadata=metadata)
        elif path.suffix == '.svg':
            document = ET.parse(path)
            assert document.getroot().tag.split('}')[-1] == 'svg'
            result.update(kind='svg')
        else:
            with Image.open(path) as image:
                result.update(kind='image', format=image.format, width=image.width, height=image.height)
                image.verify()
            with Image.open(path) as image:
                image.load()
        result['status'] = 'passed'
    except Exception as exc:
        result.update(status='failed', error=str(exc))
        errors.append(result)
    results.append(result)

lessons = []
for markdown in sorted(root.glob('*.md')):
    text = markdown.read_text()
    links = re.findall(r'\]\((assets/[^)]+)\)', text)
    missing = [link for link in links if not (root / unquote(link)).is_file()]
    assert text.count('\n```') % 2 == 0, markdown
    number = markdown.name[:2]
    article = BeautifulSoup((root / 'source' / (number + '.html')).read_text(), 'html.parser').select_one('.player___xmi1j article')
    normalized = re.sub(r'<br>|[\s*`\\>➔●•]', '', text)
    omitted = []
    for leaf in article.select('[data-cangjie-leaf=true]'):
        if leaf.find_parent('template'):
            continue
        original = re.sub(r'[\s\ufeff\u200b*`\\>➔●•]', '', leaf.get_text())
        if len(original) > 8 and original not in normalized:
            omitted.append(original[:100])
    item = {'file': markdown.name, 'local_references': len(links), 'missing': missing, 'omitted_text_segments': omitted}
    lessons.append(item)
    if missing or omitted:
        errors.append(item)

manifest = json.loads((root / 'manifest.json').read_text())
for lesson in manifest:
    for media in lesson['media']:
        if media.get('local') and not (root / media['local']).is_file():
            errors.append(media)
counts = dict(Counter(item['kind'] for item in results if item['status'] == 'passed'))
report = {'files_checked': len(results), 'counts': counts, 'markdown_files': len(lessons),
          'local_references': sum(x['local_references'] for x in lessons),
          'errors': errors, 'lessons': lessons, 'resources': results}
(root / 'resource_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
summary = (f"Markdown：{len(lessons)} 个\n本地资源：{len(results)} 个\n"
           f"类型：{json.dumps(counts, ensure_ascii=False)}\n"
           f"本地资源引用：{report['local_references']} 处\n"
           f"异常：{len(errors)} 项\n\n"
           "检查范围：资源存在性、非空、图片验证及解码、SVG XML 结构、视频时长与视频流、"
           "Markdown 与清单的本地资源链接、正文长文本片段保留情况。\n"
           "SVG 的浏览器交互行为、外部服务和脚本未执行验证。\n")
(root / '资源检查报告.txt').write_text(summary)
print(summary)
assert not errors, errors
