"""Static article URLs and sitemap shared by the daily news importer."""
import html
import json
from pathlib import Path
from bs4 import BeautifulSoup
from vk_video import enrich_vk_videos

BASE = 'https://www.wingchunspb.ru'


def document(title, body, path, description='', schema=None, noindex=False):
    title = html.escape(title)
    if 'data-vk-src=' in body:
        body += '<script src="/assets/js/vk-video.js?v=20261005" defer></script>'
    metadata = '' if schema is None else '<script type="application/ld+json">'+json.dumps(schema, ensure_ascii=False).replace('</', '<\\/')+'</script>'
    robots = 'noindex, follow' if noindex else 'index, follow, max-image-preview:large'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — IWCO СПб и ЛО</title><meta name="description" content="{html.escape(description, quote=True)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{BASE}/{path}"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:url" content="{BASE}/{path}"><meta property="og:description" content="{html.escape(description, quote=True)}"><meta property="og:image" content="{BASE}/assets/images/training-image-01.jpg"><link rel="icon" href="/assets/images/logo.png"><link rel="stylesheet" href="/assets/css/site.css?v=20261005">{metadata}</head><body class="site-document"><header><a class="site-brand" href="/">IWCO СПб и ЛО</a><nav aria-label="Основная навигация"><a href="/news.html">Новости</a><a href="/#our-classes">Залы</a><a href="/#contact-us">Запись</a></nav></header><main>{body}</main><footer><p>IWCO · Вин Чун в Санкт-Петербурге и Ленинградской области</p><p><a href="/privacy.html">Политика обработки данных</a> · <a href="/terms.html">Условия использования</a></p></footer></body></html>'''


def news_path(identity):
    return 'news/'+identity.removeprefix('tabs-')+'.html'


def write_article(identity, title, body, published=''):
    path = news_path(identity)
    soup = BeautifulSoup(enrich_vk_videos(body), 'html.parser')
    heading = soup.find('h4')
    if heading:
        heading.name = 'h1'
    for link in soup.select('.news-permalink'):
        link.decompose()
    for image in soup.find_all('img', src=True):
        if not image['src'].startswith(('http', '/')):
            image['src'] = '/'+image['src']
    for anchor in soup.find_all('a', href=True):
        if anchor['href'].startswith('assets/'):
            anchor['href'] = '/'+anchor['href']
    description = soup.select_one('.news-copy')
    description = (description.get_text(' ', strip=True) if description else soup.get_text(' ',strip=True))[:180]
    article = {'@type': 'NewsArticle', 'headline': title, 'url': BASE+'/'+path, 'mainEntityOfPage': BASE+'/'+path, 'inLanguage': 'ru-RU', 'publisher': {'@type':'Organization','name':'IWCO СПб и ЛО','url':BASE+'/'}}
    if published:
        article['datePublished'] = published
    images = [BASE+img['src'] for img in soup.find_all('img', src=True) if img['src'].startswith('/')]
    if images:
        article['image'] = images
    schema = {'@context':'https://schema.org','@graph':[article, {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Главная','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Новости','item':BASE+'/news.html'},{'@type':'ListItem','position':3,'name':title,'item':BASE+'/'+path}]}]}
    target = Path(path)
    target.parent.mkdir(exist_ok=True)
    target.write_text(document(title,str(soup),path,description,schema))
    return path


def sitemap():
    import xml.etree.ElementTree as ET
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    root = ET.Element(namespace+'urlset')
    paths = ['', 'news.html'] + [p.as_posix() for p in sorted(Path('news').glob('*.html'))]
    for path in paths:
        url = ET.SubElement(root, namespace+'url')
        ET.SubElement(url, namespace+'loc').text = BASE+'/'+path
    Path('sitemap.xml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))


def build_existing():
    import re
    page = Path('news.html').read_text()
    count = 0
    def replace(match):
        nonlocal count
        source = match.group()
        article = BeautifulSoup(source, 'html.parser').article
        title = article.find('h4').get_text(' ',strip=True)
        date = article.find('time')
        published = date.get('datetime','') if date else ''
        identity = article['id']
        path = write_article(identity,title,source,published)
        count += 1
        if 'class="news-permalink"' not in source:
            source = source.replace('</article>',f'<p class="news-permalink"><a href="/{path}">Открыть новость отдельной страницей</a></p>\n</article>')
        return source
    page = re.sub(r'<article\b[^>]*>.*?</article>',replace,page,flags=re.S)
    Path('news.html').write_text(page)
    sitemap()
    print('Built',count,'static article pages')




def refresh_archive(limit=20):
    """Keep the tab page bounded; immutable article URLs remain in the archive."""
    import re
    items = []
    for path in Path('news').glob('*.html'):
        if path.stem.startswith('archive'):
            continue
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        heading = soup.find('h1')
        if not heading:
            continue
        date = soup.find('time')
        published = date.get('datetime','') if date else ''
        title = heading.get_text(' ',strip=True)
        year = re.search(r'20\d\d',title)
        sort_date = published or ((year.group()+'-00-00') if year else '0000-00-00')
        items.append((sort_date,published,title,path.as_posix()))
    items.sort(key=lambda x: (x[0],x[2]),reverse=True)
    for previous in Path('news').glob('archive*.html'):
        previous.unlink()
    pages = max(1,(len(items)+limit-1)//limit)
    for page_number in range(pages):
        path = 'news/archive'+('' if page_number==0 else '-'+str(page_number+1))+'.html'
        links = ''.join('<li>'+ (f'<time datetime="{date}">{date}</time> · ' if date else '')+f'<a href="/{path_}">{html.escape(title)}</a></li>' for _,date,title,path_ in items[page_number*limit:(page_number+1)*limit])
        pagination = ' · '.join(f'<a href="/news/archive'+('' if i==0 else '-'+str(i+1))+f'.html">{i+1}</a>' if i!=page_number else str(i+1) for i in range(pages))
        body = f'<h1>Архив новостей IWCO</h1><p>Семинары, соревнования и события школы. Страница {page_number+1} из {pages}.</p><ul class="archive-list">{links}</ul><nav aria-label="Страницы архива">{pagination}</nav><p><a href="/news.html">Последние новости во вкладках</a></p>'
        Path(path).write_text(document('Архив новостей — страница '+str(page_number+1),body,path,'Новости Вин Чун IWCO: архив семинаров, соревнований и тренировок.'))
    page = Path('news.html').read_text()
    soup = BeautifulSoup(page,'html.parser')
    articles = soup.select('#news article')
    navigation = soup.select('#tabs > .col-lg-4 > ul li a[href^="#"]')
    keep = {link['href'][1:] for link in navigation[:limit]} if navigation else {article['id'] for article in articles[:limit]}
    for article in articles:
        if article['id'] in keep:
            continue
        identity = article['id']
        page = re.sub(r"<article id=['\"]"+re.escape(identity)+r"['\"][^>]*>.*?</article>",'',page,flags=re.S)
        page = re.sub(r"<li><a href=['\"]#"+re.escape(identity)+r"['\"][^>]*>.*?</a></li>",'',page,flags=re.S)
    if 'class="news-archive-link"' not in page:
        page = page.replace('<h1>Новости <em>Вин Чун IWCO</em></h1>','<h1>Новости <em>Вин Чун IWCO</em></h1><p class="news-archive-link"><a href="/news/archive.html">Все публикации в архиве</a></p>')
    Path('news.html').write_text(page)
    sitemap()


if __name__ == '__main__':
    build_existing()
    refresh_archive()
