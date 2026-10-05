"""Import public Telegram channels into the site's existing news tabs."""
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from datetime import datetime
from bs4 import BeautifulSoup
from site_pages import news_path, write_article, refresh_archive
from media_embeds import enrich_media

STATE = Path('data/telegram-web-news.json')
CHANNELS = Path('data/telegram-channels.json')
CHANNEL = 'iwcowingchun'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'IWCO news importer'})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(20 * 1024 * 1024 + 1)
    if len(payload) > 20 * 1024 * 1024:
        raise RuntimeError('Response exceeds size limit')
    return payload


def parse_posts(document, channel=CHANNEL):
    soup = BeautifulSoup(document, 'html.parser')
    posts = []
    for element in soup.select('.tgme_widget_message[data-post]'):
        reference = element.get('data-post', '')
        if not re.fullmatch(re.escape(channel) + r'/\d+', reference):
            continue
        text = element.select_one('.tgme_widget_message_text')
        video = bool(element.select_one('video, .tgme_widget_message_video_player'))
        photos = []
        for photo in element.select('.tgme_widget_message_photo_wrap'):
            match = re.search(r'background-image:\s*url\([\'"]?(https://[^\'"\)]+)', photo.get('style', ''))
            if match:
                photos.append(html.unescape(match.group(1)))
        if text is None and not photos and not video:
            continue
        if text:
            for unsafe in text.select('script, style, iframe, object, embed'):
                unsafe.decompose()
            for br in text.find_all('br'):
                br.replace_with('\n')
            plain = text.get_text()
            lines = [line.strip() for line in plain.splitlines() if line.strip()]
            title = next((line for line in lines if not re.match(r'^https?://', line)), 'Материал из канала ' + channel)[:160]
            for tag in list(text.find_all(True)):
                if tag.name == 'a' and re.match(r'^https?://', tag.get('href', ''), re.I):
                    tag.attrs = {'href': tag['href'], 'target': '_blank', 'rel': 'noopener noreferrer'}
                elif tag.name in ('b', 'strong', 'i', 'em', 'u', 's', 'code', 'pre'):
                    tag.attrs = {}
                else:
                    tag.unwrap()
            body = text.decode_contents().replace('\n', '<br>\n')
            body = re.sub(r'(?:<br>\s*){3,}', '<br><br>\n', body)
        else:
            title, body = 'Новость из канала ' + channel, ''
        published = next((t.get('datetime') for t in element.select('time') if t.get('datetime')), '')
        posts.append({'id': int(reference.split('/')[1]), 'reference': reference,
                      'title': title, 'body': body, 'photos': photos, 'video': video,
                      'date': published[:10]})
    return sorted(posts, key=lambda post: post['id'])


def read_channel(channel, last_id):
    found, before = {}, None
    for _ in range(100):
        url = f'https://t.me/s/{channel}' + (f'?before={before}' if before else '')
        posts = parse_posts(fetch(url).decode(), channel)
        if not posts:
            raise RuntimeError(f'No public posts found in {channel}; check channel access and markup')
        found.update({post['id']: post for post in posts})
        oldest = min(post['id'] for post in posts)
        if last_id is None or oldest <= last_id:
            return found
        if before is not None and oldest >= before:
            raise RuntimeError('Telegram pagination did not advance')
        before = oldest
    raise RuntimeError('Import history exceeds pagination limit')


def download_image(url, target):
    host = urllib.parse.urlsplit(url).hostname or ''
    if not (host.endswith('.telesco.pe') or host.endswith('.telegram-cdn.org') or host == 'telegram.org' or host.endswith('.telegram.org')):
        raise RuntimeError('Unexpected Telegram media host')
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(fetch(url))


def render_story(story):
    identity, title = story['id'], html.escape(story['title'], quote=True)
    navigation = f"<li><a href='#{identity}'>{title}</a></li>"
    images = '\n'.join(f'<img src="{html.escape(path, quote=True)}" alt="{title}" loading="lazy">' for path in story.get('images', []))
    published = story.get('date', '')
    date_label = datetime.strptime(published, '%Y-%m-%d').strftime('%d.%m.%Y') if published else ''
    date = f'<p class="news-date"><time datetime="{published}">{date_label}</time></p>' if published else ''
    videos = '\n'.join(f'<div class="news-video-link"><p><a href="https://t.me/{reference}" target="_blank" rel="noopener noreferrer">Смотреть видео в Telegram</a></p></div>' for reference in story.get('videos', []))
    channel = story.get('channel', CHANNEL)
    sources = ' · '.join(f'<a href="https://t.me/{channel}/{number}" target="_blank" rel="noopener noreferrer">Публикация {number}</a>' for number in story.get('source_ids', []))
    article = f"<article id='{identity}' class='news-article'>\n{images}\n<h4>{title}</h4>\n{date}\n<div class=\"news-copy\">{story['body']}</div>\n{videos}\n<p class=\"news-sources\">Источник: {sources}</p>\n</article>"
    article = article.replace('</article>', f'<p class="news-permalink"><a href="/{news_path(identity)}">Открыть новость отдельной страницей</a></p>\n</article>')
    return navigation, enrich_media(article)


def insert_stories(stories):
    page = Path('news.html')
    source = page.read_text()
    existing = {article['id'] for article in BeautifulSoup(source, 'html.parser').select('article[id]')}
    navigation, articles = [], []
    for story in sorted(stories, key=lambda item: (item.get('date', ''), max(item.get('source_ids', [0]))), reverse=True):
        if story['id'] in existing:
            continue
        nav, article = render_story(story)
        navigation.append(nav)
        articles.append(article)
        write_article(story['id'],story['title'],article,story.get('date',''))
    for marker, additions in [('<!-- TELEGRAM_NEWS_NAV -->', navigation), ('<!-- TELEGRAM_NEWS_ARTICLES -->', articles)]:
        if source.count(marker) != 1:
            raise RuntimeError('Missing or duplicate news insertion marker')
        if additions:
            source = source.replace(marker, marker + '\n' + '\n'.join(additions))
    if articles:
        page.write_text(source)
        refresh_archive()
    return len(articles)


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {'channels': {}}
    # Upgrade the original single-channel watermark without replaying old posts.
    if 'last_id' in state:
        state['channels'] = {CHANNEL: {'last_id': state.pop('last_id')}}
    channels = json.loads(CHANNELS.read_text()) if CHANNELS.exists() else [CHANNEL]
    stories = []
    for channel in channels:
        if not re.fullmatch(r'[A-Za-z0-9_]{5,32}', channel):
            raise RuntimeError('Invalid public channel username')
        watermark = state['channels'].get(channel, {}).get('last_id')
        found = read_channel(channel, watermark)
        if watermark is not None:
            for post in found.values():
                if post['id'] <= watermark:
                    continue
                images = []
                for index, url in enumerate(post['photos']):
                    target = Path(f'assets/images/news/telegram-{channel}-{post["id"]}-{index}.jpg')
                    download_image(url, target)
                    images.append(target.as_posix())
                stories.append({'id': f'tabs-tg-{channel}-{post["id"]}', 'title': post['title'],
                                'date': post['date'], 'body': post['body'], 'images': images,
                                'videos': [post['reference']] if post['video'] else [],
                                'source_ids': [post['id']], 'channel': channel})
        state['channels'][channel] = {'last_id': max(found)}
    added = insert_stories(stories) if stories else 0
    STATE.parent.mkdir(exist_ok=True)
    serialized = json.dumps(state, ensure_ascii=False, indent=2) + '\n'
    if not STATE.exists() or STATE.read_text() != serialized:
        STATE.write_text(serialized)
    print(f'Added {added} news tabs' if added else 'No new news; no publication needed')


if __name__ == '__main__':
    main()
