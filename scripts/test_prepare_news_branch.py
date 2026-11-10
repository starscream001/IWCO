"""Exercise rejection cleanup against a real Git history without GitHub access."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import prepare_news_branch as prepare


class PrepareTests(unittest.TestCase):
    def test_closed_pr_removes_files_and_keeps_cursors_on_repeated_runs(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                def git(*args):
                    return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL).strip()
                git('init', '-b', 'main')
                git('config', 'user.name', 'Test')
                git('config', 'user.email', 'test@example.com')
                prepare.STATE.parent.mkdir()
                prepare.STATE.write_text(json.dumps({'channels': {'iwcowingchun': {'last_id': 1}}}))
                Path('news.html').write_text('Published 1')
                git('add', '.')
                git('commit', '-m', 'Published')
                git('update-ref', 'refs/remotes/origin/main', 'HEAD')
                Path('news.html').write_text('Published 1 + pending 2')
                Path('rejected.html').write_text('2')
                prepare.STATE.write_text(json.dumps({'channels': {'iwcowingchun': {'last_id': 2}}, 'notified_pr': 'old'}))
                git('add', '.')
                git('commit', '-m', 'Pending')
                git('update-ref', 'refs/remotes/origin/codex/telegram-news', 'HEAD')
                real_run = prepare.run
                def run(*args):
                    if args[0] == 'gh':
                        return '[{"number": 2, "state": "CLOSED"}]'
                    return real_run(*args)
                with patch.dict(os.environ, {'NEWS_BRANCH': 'codex/telegram-news', 'BASE_BRANCH': 'main'}), patch.object(prepare, 'run', side_effect=run):
                    for _ in range(2):
                        prepare.main()
                        self.assertEqual(Path('news.html').read_text(), 'Published 1')
                        self.assertFalse(Path('rejected.html').exists())
                        state = json.loads(prepare.STATE.read_text())
                        self.assertEqual(state['channels']['iwcowingchun']['last_id'], 2)
                        self.assertNotIn('notified_pr', state)
                        git('update-ref', 'refs/remotes/origin/codex/telegram-news', 'HEAD')
            finally:
                os.chdir(original)
