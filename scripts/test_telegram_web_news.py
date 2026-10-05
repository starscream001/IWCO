import unittest
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import telegram_web_news as news
from telegram_web_news import parse_posts


class WebNewsTests(unittest.TestCase):
    def test_public_post_sanitization_and_video(self):
        posts = parse_posts('''<div class="tgme_widget_message" data-post="iwcowingchun/5"><div class="tgme_widget_message_text"><b onclick="bad()">Title</b><br>Text <a href="javascript:bad()">bad</a><a href="https://example.com">ok</a></div><video src="video.mp4"></video></div><div class="tgme_widget_message" data-post="other/6"><div class="tgme_widget_message_text">Ignore</div></div>''')
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['title'], 'Title')
        self.assertTrue(posts[0]['video'])
        self.assertNotIn('onclick', posts[0]['body'])
        self.assertNotIn('javascript:', posts[0]['body'])
        self.assertIn('<b>Title</b><br>', posts[0]['body'])

    def test_album_photos(self):
        posts = parse_posts('''<div class="tgme_widget_message" data-post="iwcowingchun/8"><a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn4.telesco.pe/a.jpg')"></a><a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn4.telesco.pe/b.jpg')"></a></div>''')
        self.assertEqual(len(posts), 1)
        self.assertEqual(len(posts[0]['photos']), 2)

    def test_import_persists_watermark_and_does_not_duplicate(self):
        document = b'<div class="tgme_widget_message" data-post="iwcowingchun/8"><div class="tgme_widget_message_text">Older</div></div><div class="tgme_widget_message" data-post="iwcowingchun/9"><div class="tgme_widget_message_text">New</div><video></video></div>'
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                news.STATE.parent.mkdir()
                news.STATE.write_text(json.dumps({'last_id': 8}))
                Path('news.html').write_text('<!-- TELEGRAM_NEWS_NAV --><!-- TELEGRAM_NEWS_ARTICLES -->')
                with patch.object(news, 'fetch', return_value=document):
                    news.main()
                    first = Path('news.html').read_text()
                    news.main()
                self.assertEqual(first, Path('news.html').read_text())
                self.assertEqual(first.count('<article '), 1)
                self.assertIn('href="https://t.me/iwcowingchun/9"', first)
                self.assertIn('New</div>', first)
                self.assertNotIn('data-telegram-post', first)
                self.assertNotIn('telegram-widget', first)
                self.assertEqual(json.loads(news.STATE.read_text())['channels']['iwcowingchun']['last_id'], 9)
            finally:
                os.chdir(original)
