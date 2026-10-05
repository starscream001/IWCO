import unittest
from bs4 import BeautifulSoup
from media_embeds import media_source,enrich_media

class MediaTests(unittest.TestCase):
    def test_public_sources_and_no_autoplay(self):
        item=media_source('https://rutube.ru/video/22b50ec877adf433779b2a327658231e/?t=30&autoplay=true')
        self.assertIn('autoplay=false',item[1]);self.assertIn('t=30',item[1])
        self.assertEqual(media_source('https://t.me/s/iwcowingchun/431')[1],'iwcowingchun/431')
    def test_reject_other_hosts_private_posts_and_profiles(self):
        for value in ['https://rutube.ru.evil/video/'+'a'*32,'https://t.me/+private','https://t.me/iwcowingchun','javascript:alert(1)','https://t.me:bad/iwcowingchun/431']:
            self.assertIsNone(media_source(value))
    def test_deduplicate_and_keep_local_text_no_initial_frames(self):
        fragment='<article><div class="news-copy"><p>Местный текст</p><a href="https://t.me/iwcowingchun/431">Видео</a><a href="https://t.me/s/iwcowingchun/431">Ещё ссылка</a></div><p class="news-sources"><a href="https://t.me/iwcowingchun/432">Источник</a></p></article>'
        result=enrich_media(fragment);soup=BeautifulSoup(result,'html.parser')
        self.assertEqual(len(soup.select('.media-embed')),1);self.assertFalse(soup.find('iframe'));self.assertFalse(soup.find('script'));self.assertIn('Местный текст',soup.get_text())
        self.assertEqual(result,enrich_media(result))
