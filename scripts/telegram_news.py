"""Notify the owner once per news PR; keep the bot token out of public assets."""
import json
import html
import os
from pathlib import Path
import sys
import urllib.request

STATE = Path('data/telegram-web-news.json')


def notify():
    state = json.loads(STATE.read_text())
    url = os.environ['PR_URL']
    if state.get('notified_pr') == url:
        return
    token = os.environ['TELEGRAM_BOT_TOKEN']
    request = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=json.dumps({'chat_id': os.environ['TELEGRAM_CHAT_ID'],
                         'text': '<b>Новости IWCO · создан PR</b>\n\n<a href="' + html.escape(url, quote=True) + '">Открыть и проверить новости</a>\n\nПосле слияния новости появятся на сайте.', 'parse_mode': 'HTML', 'link_preview_options': {'is_disabled': True}}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
        if not result.get('ok'):
            raise RuntimeError('Telegram rejected notification')
    except Exception:
        raise RuntimeError('Telegram notification failed; check token and recipient ID') from None
    state['notified_pr'] = url
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    if sys.argv[1:] != ['notify']:
        sys.exit('Usage: telegram_news.py notify')
    try:
        notify()
    except Exception as error:
        print(f'Notification failed ({type(error).__name__}); check configuration and Telegram availability.', file=sys.stderr)
        sys.exit(1)
