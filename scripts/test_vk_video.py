import unittest
from bs4 import BeautifulSoup
from vk_video import player_url, enrich_vk_videos
from telegram_web_news import render_story


class VKVideoTests(unittest.TestCase):
    def test_domains_and_start_time(self):
        self.assertEqual(player_url('https://vkvideo.ru/video-22560541_456239157?t=3m45s'),
                         'https://vkvideo.ru/video_ext.php?oid=-22560541&id=456239157&hd=3&t=3m45s')
        self.assertEqual(player_url('https://vk.com/video?z=video-22560541_456239159%2Fabc'),
                         'https://vkvideo.ru/video_ext.php?oid=-22560541&id=456239159&hd=3')
        self.assertIn('&t=30s', player_url('https://vk.ru/video10_20?t=30'))
        self.assertIn('oid=-10&id=20', player_url('https://vk.com/videos-10?z=video-10_20%2Fclub10'))

    def test_rejects_non_video_and_spoofed_hosts(self):
        for url in ['https://vk.com/album-10_20', 'https://vkvideo.ru/clip-10_20',
                    'https://vkvideo.ru.evil.test/video10_20', 'https://vkvideo.ru@evil.test/video10_20',
                    'javascript:alert(1)', 'https://vkvideo.ru/video0_20', 'https://vkvideo.ru/video10_0']:
            self.assertIsNone(player_url(url), url)

    def test_deduplication_and_idempotence(self):
        fragment='<article><h4>Видео</h4><div class="news-copy"><a href="https://vk.com/video-10_20">VK</a><a href="https://vkvideo.ru/video-10_20?t=5s">Повтор</a></div></article>'
        rendered=enrich_vk_videos(fragment)
        soup=BeautifulSoup(rendered, 'html.parser')
        self.assertEqual(len(soup.select('.vk-video')),1)
        self.assertFalse(soup.find('iframe'))
        self.assertEqual(rendered,enrich_vk_videos(rendered))
        self.assertEqual(len(soup.select('.news-copy a')),2)

    def test_existing_embed_preserves_public_signature(self):
        fragment='<article><div class="video-wrapper"><iframe src="https://vkvideo.ru/video_ext.php?oid=-10&id=20&hash=5a3fcf2a0dadc03e&autoplay=1"></iframe></div><a href="https://vk.com/video-10_20">Источник</a></article>'
        soup=BeautifulSoup(enrich_vk_videos(fragment),'html.parser')
        self.assertEqual(len(soup.select('.vk-video')),1)
        self.assertIn('hash=5a3fcf2a0dadc03e',soup.select_one('.vk-video')['data-vk-src'])
        self.assertNotIn('autoplay',soup.select_one('.vk-video')['data-vk-src'])

    def test_new_post_contains_vk_player_and_telegram_fallback(self):
        _,article=render_story({'id':'tabs-tg-testchannel-15','title':'Новость','body':'<a href="https://vkvideo.ru/video-10_20">Ролик</a>',
                               'videos':['testchannel/15'],'channel':'testchannel','source_ids':[15]})
        self.assertIn('data-vk-src=',article)
        self.assertIn('https://t.me/testchannel/15',article)
        self.assertIn('Смотреть видео ВКонтакте',article)
