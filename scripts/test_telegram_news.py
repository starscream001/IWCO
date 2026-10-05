import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import telegram_news as news


class NotificationTests(unittest.TestCase):
    def test_success_and_duplicate_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'last_id': 432}))
            with patch.object(news, 'STATE', state), patch.dict(os.environ, PR_URL='https://github.com/test/repo/pull/1', TELEGRAM_BOT_TOKEN='test-secret', TELEGRAM_CHAT_ID='123'), patch.object(news.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"ok":true}')) as api:
                news.notify()
                news.notify()
            self.assertEqual(api.call_count, 1)
            self.assertEqual(json.loads(state.read_text())['last_id'], 432)

    def test_failed_notification_can_retry_and_hides_token(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'last_id': 432}))
            with patch.object(news, 'STATE', state), patch.dict(os.environ, PR_URL='https://github.com/test/repo/pull/1', TELEGRAM_BOT_TOKEN='test-secret', TELEGRAM_CHAT_ID='123'), patch.object(news.urllib.request, 'urlopen', side_effect=RuntimeError('URL containing test-secret')):
                with self.assertRaises(RuntimeError) as result:
                    news.notify()
            self.assertNotIn('test-secret', str(result.exception))
            self.assertNotIn('notified_pr', json.loads(state.read_text()))


if __name__ == '__main__':
    unittest.main()
