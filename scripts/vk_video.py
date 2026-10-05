"""Recognize public VK video URLs without network requests or credentials."""
import html
import re
from urllib.parse import urlsplit, parse_qs, urlencode
from bs4 import BeautifulSoup

HOSTS = {'vk.com', 'www.vk.com', 'm.vk.com', 'vk.ru', 'www.vk.ru', 'm.vk.ru', 'vkvideo.ru', 'www.vkvideo.ru'}


def player_url(value):
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    if url.scheme not in ('http', 'https') or url.hostname not in HOSTS or url.username or url.password:
        return None
    query = parse_qs(url.query)
    match = re.fullmatch(r'/video(-?\d{1,18})_(\d{1,18})/?', url.path)
    if not match:
        for key in ('z', 'w'):
            match = re.match(r'^video(-?\d{1,18})_(\d{1,18})(?:/|$)', query.get(key, [''])[0])
            if match:
                break
    if match:
        owner, video = match.groups()
    elif url.path == '/video_ext.php':
        owner, video = query.get('oid', [''])[0], query.get('id', [''])[0]
        if not re.fullmatch(r'-?\d{1,18}', owner) or not re.fullmatch(r'\d{1,18}', video):
            return None
    else:
        return None
    if int(owner) == 0 or int(video) == 0:
        return None
    params = {'oid': str(int(owner)), 'id': str(int(video)), 'hd': '3'}
    signature = query.get('hash', [''])[0]
    if re.fullmatch(r'[a-fA-F0-9]{16,64}', signature):
        params['hash'] = signature
    start = query.get('t', [''])[0]
    if re.fullmatch(r'\d{1,6}', start):
        params['t'] = start + 's'
    elif start and re.fullmatch(r'(?:\d{1,3}h)?(?:\d{1,3}m)?(?:\d{1,3}s)?', start):
        params['t'] = start
    return 'https://vkvideo.ru/video_ext.php?' + urlencode(params)


def identity(url):
    query = parse_qs(urlsplit(url).query)
    return query['oid'][0], query['id'][0]


def card(url):
    owner, video = identity(url)
    src = html.escape(url, quote=True)
    link = f'https://vkvideo.ru/video{owner}_{video}'
    return BeautifulSoup(f'''<div class="vk-video" data-vk-src="{src}">
<div class="vk-video-stage"><button type="button" class="vk-video-play" aria-label="Смотреть видео ВКонтакте"><span class="vk-play-symbol" aria-hidden="true">▶</span><span>Смотреть видео ВКонтакте</span></button></div>
<p class="vk-video-caption">Плеер VK загружается после нажатия. <a href="{link}" target="_blank" rel="noopener noreferrer">Открыть видео в VK</a></p>
</div>''', 'html.parser').div


def enrich_vk_videos(fragment):
    """Add one click-to-load player per video; retain source links as fallback."""
    soup = BeautifulSoup(fragment, 'html.parser')
    seen = set()
    for existing in soup.select('.vk-video[data-vk-src]'):
        url = player_url(existing['data-vk-src'])
        if url:
            seen.add(identity(url))
    for frame in soup.find_all('iframe', src=True):
        url = player_url(frame['src'])
        if not url:
            continue
        parent = frame.parent
        target = parent if 'video-wrapper' in parent.get('class', []) else frame
        if identity(url) in seen:
            target.decompose()
        else:
            target.replace_with(card(url))
            seen.add(identity(url))
    additions = []
    for anchor in soup.find_all('a', href=True):
        url = player_url(anchor['href'])
        if url and identity(url) not in seen:
            additions.append(card(url))
            seen.add(identity(url))
    after = soup.select_one('.news-copy')
    for addition in additions:
        if after:
            after.insert_after(addition)
            after = addition
        else:
            (soup.article or soup).append(addition)
    return str(soup)
