"""Small contact endpoint. Secrets and replay state remain on the server."""
import base64
import hashlib
import html
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request

ORIGINS = set(os.environ.get('ALLOWED_ORIGINS', 'https://www.wingchunspb.ru,https://wingchunspb.ru,https://starscream001.github.io').split(','))
HALLS = {'м. Горьковская', 'м. Удельная', 'м. Ладожская', 'Гатчина'}
DATABASE = os.environ.get('STATE_DB', '/state/contact.sqlite3')


def db():
    connection = sqlite3.connect(DATABASE, timeout=5)
    connection.execute('CREATE TABLE IF NOT EXISTS used_challenges (nonce TEXT PRIMARY KEY, expires INTEGER)')
    connection.execute('CREATE TABLE IF NOT EXISTS consent_receipts (nonce TEXT PRIMARY KEY, created INTEGER, version TEXT, submission_hash TEXT, delivered INTEGER DEFAULT 0)')
    return connection


def secret():
    return os.environ['CHALLENGE_SECRET'].encode()


def challenge():
    stamp = int(time.time())
    value = f'{stamp}.{secrets.token_hex(16)}'
    signature = hmac.new(secret(), value.encode(), hashlib.sha256).hexdigest()
    return value + '.' + signature


def consume_challenge(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError('Обновите страницу и попробуйте снова.')
    try:
        stamp, nonce, signature = value.split('.')
        issued = int(stamp)
    except (ValueError, AttributeError):
        raise ValueError('Обновите страницу и попробуйте снова.') from None
    expected = hmac.new(secret(), f'{stamp}.{nonce}'.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected) or not 2 <= time.time() - issued <= 1800:
        raise ValueError('Подождите пару секунд или обновите страницу и попробуйте снова.')
    with db() as connection:
        connection.execute('DELETE FROM used_challenges WHERE expires < ?', (int(time.time()),))
        try:
            connection.execute('INSERT INTO used_challenges VALUES (?, ?)', (nonce, issued + 1800))
        except sqlite3.IntegrityError:
            raise ValueError('Эта заявка уже отправлялась. Обновите страницу.') from None


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Некорректная заявка.')
    if data.get('consent') is not True or data.get('consent_version') != '2026-10-05':
        raise ValueError('Подтвердите согласие на обработку персональных данных.')
    limits = {'name': (2, 100), 'phone': (7, 40), 'hall': (1, 80), 'message': (1, 2000)}
    result = {}
    for field, (minimum, maximum) in limits.items():
        value = data.get(field)
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ValueError('Проверьте имя, телефон, зал и сообщение.')
        result[field] = value.strip()
    digits = ''.join(char for char in result['phone'] if char.isascii() and char.isdigit())
    if not 7 <= len(digits) <= 15 or result['hall'] not in HALLS:
        raise ValueError('Проверьте телефон и выберите зал.')
    return result


def record_consent(data, nonce):
    created = int(time.time())
    # A nonce salts the digest; the receipt database retains no submitted text.
    digest = hashlib.sha256((nonce + json.dumps(data, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    with db() as connection:
        connection.execute('DELETE FROM consent_receipts WHERE created < ?', (created - 365 * 86400,))
        connection.execute('INSERT INTO consent_receipts (nonce, created, version, submission_hash) VALUES (?, ?, ?, ?)', (nonce, created, '2026-10-05', digest))
    return nonce


def send(data, receipt=None):
    message = '\n'.join(['<b>Новая заявка · IWCO</b>', '<b>Имя:</b> ' + html.escape(data['name']), '<b>Телефон:</b> ' + html.escape(data['phone']), '<b>Зал:</b> ' + html.escape(data['hall']), '', '<b>Сообщение:</b>', html.escape(data['message'])])
    if receipt:
        from datetime import datetime, timezone, timedelta
        stamp = datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M МСК')
        message += '\n\n<b>Согласие:</b> версия 2026-10-05, ' + stamp + '\n<b>Заявка:</b> ' + html.escape(receipt)
    request = urllib.request.Request(
        'https://api.telegram.org/bot' + os.environ['TELEGRAM_BOT_TOKEN'] + '/sendMessage',
        data=json.dumps({'chat_id': os.environ['TELEGRAM_CHAT_ID'], 'text': message, 'parse_mode': 'HTML', 'link_preview_options': {'is_disabled': True}}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if not json.load(response).get('ok'):
                raise RuntimeError('Telegram rejected request')
    except Exception:
        raise RuntimeError('Не удалось отправить заявку. Попробуйте позже или позвоните нам.') from None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Do not retain names, phone numbers, messages or token-bearing URLs in logs.
        pass

    def respond(self, status, payload=None):
        body = json.dumps(payload or {}, ensure_ascii=False).encode()
        self.send_response(status)
        origin = self.headers.get('Origin')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.respond(200 if self.headers.get('Origin') in ORIGINS else 403)

    def do_GET(self):
        if self.path == '/healthz':
            self.respond(200, {'ok': True, 'configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN'))})
        elif self.path == '/api/challenge' and self.headers.get('Origin') in ORIGINS:
            self.respond(200, {'challenge': challenge()})
        else:
            self.respond(404)

    def do_POST(self):
        if self.path != '/api/contact':
            self.respond(404)
            return
        if self.headers.get('Origin') not in ORIGINS:
            self.respond(403)
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.respond(415)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                self.respond(413)
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Некорректная заявка.')
            if data.get('website'):
                self.respond(200, {'ok': True})
                return
            fields = validate(data)
            consume_challenge(data.get('challenge'))
            nonce = data['challenge'].split('.')[1]
            receipt = record_consent(fields, nonce)
            send(fields, receipt)
            with db() as connection:
                connection.execute('UPDATE consent_receipts SET delivered = 1 WHERE nonce = ?', (nonce,))
            self.respond(200, {'ok': True})
        except (ValueError, UnicodeError) as error:
            # JSON errors may contain user input; return a generic validation error.
            message = str(error) if not isinstance(error, json.JSONDecodeError) else 'Некорректная заявка.'
            self.respond(400, {'error': message})
        except Exception:
            self.respond(502, {'error': 'Не удалось отправить заявку. Попробуйте позже или позвоните нам.'})


if __name__ == '__main__':
    with db():
        pass
    import threading
    def cleanup_receipts():
        while True:
            with db() as connection:
                connection.execute('DELETE FROM consent_receipts WHERE created < ?', (int(time.time()) - 365 * 86400 + 3600,))
            time.sleep(3600)
    threading.Thread(target=cleanup_receipts, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
