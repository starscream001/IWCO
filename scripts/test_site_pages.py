import json
import os
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup
from site_pages import write_article, refresh_archive


class SitePagesTests(unittest.TestCase):
    def test_archive_bounds_index_and_retains_searchable_pages(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                articles=[]
                links=[]
                for number in range(25):
                    identity=f'tabs-tg-testchannel-{number}'
                    article=f'<article id="{identity}"><h4>Новость {number}</h4><p class="news-date"><time datetime="2026-10-01">01.10.2026</time></p><img src="assets/images/photo.jpg" alt="Тренировка"><div class="news-copy">Описание новости</div></article>'
                    write_article(identity,f'Новость {number}',article,'2026-10-01')
                    articles.append(article)
                    links.append(f'<li><a href="#{identity}">Новость {number}</a></li>')
                Path('news.html').write_text('<section id="news"><ul>'+''.join(links)+'</ul>'+''.join(articles)+'</section>')
                refresh_archive()
                index=BeautifulSoup(Path('news.html').read_text(),'html.parser')
                self.assertEqual(len(index.find_all('article')),20)
                self.assertEqual(len(index.select('li a')),20)
                self.assertEqual(len(list(Path('news').glob('tg-*.html'))),25)
                self.assertTrue(Path('news/archive-2.html').exists())
                self.assertIn('tg-testchannel-24.html',Path('sitemap.xml').read_text())
                page=BeautifulSoup(Path('news/tg-testchannel-24.html').read_text(),'html.parser')
                self.assertEqual(len(page.find_all('h1')),1)
                self.assertEqual(page.img['src'],'/assets/images/photo.jpg')
                schema=json.loads(page.find('script',type='application/ld+json').string)
                self.assertEqual(schema['@graph'][0]['headline'],'Новость 24')
            finally:
                os.chdir(original)
