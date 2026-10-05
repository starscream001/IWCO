"""Public Rutube videos and Telegram posts, loaded only on visitor request."""
import html
import re
from urllib.parse import urlsplit, parse_qs, urlencode
from bs4 import BeautifulSoup
from vk_video import enrich_vk_videos


def media_source(value):
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        return None
    if url.scheme not in ('http', 'https') or url.username or url.password or port not in (None, 80, 443):
        return None
    if url.hostname in ('rutube.ru', 'www.rutube.ru'):
        match = re.fullmatch(r'/(?:video|play/embed)/([a-fA-F0-9]{32})/?', url.path)
        if match:
            video = match[1].lower()
            params = {'autoplay': 'false'}
            start = parse_qs(url.query).get('t', [''])[0]
            if re.fullmatch(r'\d{1,6}', start):
                params['t'] = start
            return 'rutube', 'https://rutube.ru/play/embed/'+video+'?'+urlencode(params), 'https://rutube.ru/video/'+video+'/'
    if url.hostname in ('t.me', 'telegram.me', 'www.t.me'):
        match = re.fullmatch(r'/(?:s/)?([a-zA-Z][a-zA-Z0-9_]{3,31})/([1-9]\d{0,12})/?', url.path)
        if match:
            post = match[1]+'/'+match[2]
            return 'telegram', post, 'https://t.me/'+post
    return None


def enrich_media(fragment):
    soup = BeautifulSoup(enrich_vk_videos(fragment), 'html.parser')
    seen = {(node.get('data-provider'), node.get('data-media-src')) for node in soup.select('.media-embed')}
    additions = []
    for anchor in soup.find_all('a', href=True):
        # Attribution links are not media. Telegram video links and explicit
        # links within the locally stored article body are eligible.
        if anchor.find_parent(class_='news-sources') or anchor.find_parent(class_='media-embed'):
            continue
        item = media_source(anchor['href'])
        if not item:
            continue
        provider, source, link = item
        if (provider, source) in seen:
            continue
        seen.add((provider, source))
        label = 'Rutube' if provider == 'rutube' else 'Telegram'
        action = 'Смотреть видео в Rutube' if provider == 'rutube' else 'Открыть публикацию Telegram здесь'
        additions.append(BeautifulSoup(f'''<div class="media-embed" data-provider="{provider}" data-media-src="{html.escape(source,quote=True)}"><div class="media-stage"><button type="button" class="media-play"><span class="vk-play-symbol" aria-hidden="true">▶</span><span>{action}</span></button></div><p class="media-caption">{label} загружается после нажатия. <a href="{link}" target="_blank" rel="noopener noreferrer">Открыть в {label}</a></p></div>''','html.parser').div)
    after = soup.select_one('.news-copy')
    for node in additions:
        if after:
            after.insert_after(node)
            after = node
        else:
            (soup.article or soup).append(node)
    return str(soup)
