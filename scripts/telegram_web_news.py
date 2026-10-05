"""Import public channel posts. Bot token is used only for PR notifications."""
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

STATE = Path('data/telegram-web-news.json')
CHANNEL = 'iwcowingchun'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'IWCO news importer'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise RuntimeError('Response exceeds size limit')
    return data


def parse_posts(document):
    soup = BeautifulSoup(document, 'html.parser')
    posts = []
    for element in soup.select('.tgme_widget_message[data-post]'):
        reference = element.get('data-post', '')
        if not re.fullmatch(CHANNEL + r'/\d+', reference):
            continue
        text = element.select_one('.tgme_widget_message_text')
        # Keep the original Telegram post via its official widget for videos.
        video = bool(element.select_one('video, .tgme_widget_message_video_player'))
        photos = []
        for photo in element.select('.tgme_widget_message_photo_wrap'):
            match = re.search(r'background-image:\s*url\([\'"]?(https://[^\'"\)]+)', photo.get('style', ''))
            if match:
                photos.append(html.unescape(match.group(1)))
        if text is None and not photos and not video:
            continue
        if text:
            for br in text.find_all('br'):
                br.replace_with('\n')
            title = next((line.strip() for line in text.get_text().splitlines() if line.strip()), 'Новость')[:160]
            # Strip all attributes except safe external link targets and formatting.
            for tag in list(text.find_all(True)):
                if tag.name == 'a' and re.match(r'^https?://', tag.get('href', ''), re.I):
                    tag.attrs = {'href': tag['href'], 'target': '_blank', 'rel': 'noopener noreferrer'}
                elif tag.name in ('b', 'strong', 'i', 'em', 'u', 's', 'code', 'pre'):
                    tag.attrs = {}
                else:
                    tag.unwrap()
            body = text.decode_contents().replace('\n', '<br>\n')
        else:
            title, body = 'Новость из Telegram', ''
        posts.append({'id': int(reference.split('/')[1]), 'reference': reference,
                      'title': title, 'body': body, 'photos': photos, 'video': video})
    return sorted(posts, key=lambda post: post['id'])


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else None
    pages, before = [], None
    # Walk backwards until the saved watermark to cover busy periods and downtime.
    for _ in range(100):
        url = f'https://t.me/s/{CHANNEL}' + (f'?before={before}' if before else '')
        posts = parse_posts(fetch(url).decode())
        if not posts:
            raise RuntimeError('No public posts found; Telegram markup may have changed')
        pages.extend(posts)
        if state is None or min(p['id'] for p in posts) <= state['last_id']:
            break
        oldest = min(p['id'] for p in posts)
        if before is not None and oldest >= before:
            raise RuntimeError('Telegram pagination did not advance')
        before = oldest
    else:
        raise RuntimeError('Import history exceeds pagination limit')
    STATE.parent.mkdir(exist_ok=True)
    if state is None:
        # First run starts monitoring now, rather than publishing the whole archive.
        STATE.write_text(json.dumps({'last_id': max(p['id'] for p in pages)}) + '\n')
        print('Initialized channel watermark; future posts will be imported')
        return
    posts = {p['id']: p for p in pages if p['id'] > state['last_id']}
    if not posts:
        print('No new posts')
        return
    page = Path('news.html')
    source = page.read_text()
    nav, articles = [], []
    for post in sorted(posts.values(), key=lambda p: p['id'], reverse=True):
        identity = f'tabs-tg-{post["id"]}'
        title = html.escape(post['title'], quote=True)
        images = []
        for index, url in enumerate(post['photos']):
            host = urllib.parse.urlsplit(url).hostname or ''
            if not (host.endswith('.telesco.pe') or host.endswith('.telegram-cdn.org') or host == 'telegram.org' or host.endswith('.telegram.org')):
                raise RuntimeError('Unexpected Telegram media host')
            target = Path(f'assets/images/news/telegram-{post["id"]}-{index}.jpg')
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(fetch(url))
            images.append(f'<img src="{target}" alt="{title}" loading="lazy">')
        reference = post['reference']
        widget = (f'<script async src="https://telegram.org/js/telegram-widget.js?22" data-telegram-post="{reference}" data-width="100%"></script>' if post['video'] else '')
        nav.append(f"<li><a href='#{identity}'>{title}</a></li>")
        articles.append(f"<article id='{identity}'>\n" + '\n'.join(images) + f'\n<h4>{title}</h4>\n<p>{post["body"]}</p>\n{widget}\n<p><a href="https://t.me/{reference}" target="_blank" rel="noopener noreferrer">Пост в Telegram</a></p>\n</article>')
    for marker, additions in [('<!-- TELEGRAM_NEWS_NAV -->', nav), ('<!-- TELEGRAM_NEWS_ARTICLES -->', articles)]:
        if source.count(marker) != 1:
            raise RuntimeError('Missing or duplicate news insertion marker')
        source = source.replace(marker, marker + '\n' + '\n'.join(additions))
    page.write_text(source)
    state['last_id'] = max(posts)
    STATE.write_text(json.dumps(state) + '\n')
    print(f'Added {len(posts)} news tabs')


if __name__ == '__main__':
    main()
