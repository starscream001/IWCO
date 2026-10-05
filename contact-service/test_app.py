import io
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import app


class ContactTests(unittest.TestCase):
    def test_fields(self):
        good = {'name': 'Илья', 'phone': '+7 911 123 45 67', 'hall': 'Гатчина', 'message': 'Хочу записаться'}
        self.assertEqual(app.validate(good), good)
        for field, value in [('phone', 'abc'), ('hall', 'Unknown'), ('message', 'x' * 2001)]:
            with self.assertRaises(ValueError):
                app.validate({**good, field: value})

    def test_challenge_signature_expiry_and_replay(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'DATABASE', str(Path(directory)/'test.db')), patch.dict(os.environ, CHALLENGE_SECRET='test-secret'):
            with patch.object(app.time, 'time', return_value=1000):
                token = app.challenge()
            with patch.object(app.time, 'time', return_value=1003):
                app.consume_challenge(token)
                with self.assertRaises(ValueError):
                    app.consume_challenge(token)
                with self.assertRaises(ValueError):
                    app.consume_challenge(token[:-1] + 'z')
            with patch.object(app.time, 'time', return_value=4000), self.assertRaises(ValueError):
                app.consume_challenge(token)

    def test_telegram_failure_does_not_leak_token(self):
        with patch.dict(os.environ, TELEGRAM_BOT_TOKEN='private-token', TELEGRAM_CHAT_ID='1'), patch.object(app.urllib.request, 'urlopen', side_effect=RuntimeError('private-token')):
            with self.assertRaises(RuntimeError) as result:
                app.send({'name':'Илья','phone':'123456789','hall':'Гатчина','message':'Test'})
            self.assertNotIn('private-token', str(result.exception))
