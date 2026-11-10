"""Discard rejected publication content while preserving per-channel read cursors."""
import json
import os
from pathlib import Path
import subprocess

STATE = Path('data/telegram-web-news.json')


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def merge_cursors(base, pending):
    result = json.loads(json.dumps(base))
    channels = result.setdefault('channels', {})
    for channel, cursor in pending.get('channels', {}).items():
        channels[channel] = {'last_id': max(cursor['last_id'], channels.get(channel, {}).get('last_id', 0))}
    result.pop('notified_pr', None)
    return result


def main():
    branch, base = os.environ['NEWS_BRANCH'], 'origin/' + os.environ['BASE_BRANCH']
    exists = subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/remotes/origin/' + branch]).returncode == 0
    if not exists:
        run('git', 'checkout', '-b', branch, base)
        return
    prs = json.loads(run('gh', 'pr', 'list', '--head', branch, '--base', os.environ['BASE_BRANCH'], '--state', 'all', '--limit', '100', '--json', 'number,state'))
    latest = max(prs, key=lambda pr: pr['number'], default={})
    run('git', 'checkout', '-B', branch, 'origin/' + branch)
    if latest.get('state') == 'CLOSED':
        pending = json.loads(STATE.read_text())
        # Restore the published site, including removal of rejected article files.
        run('git', 'restore', '--source', base, '--staged', '--worktree', '.')
        state = merge_cursors(json.loads(STATE.read_text()), pending)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        run('git', 'add', str(STATE))
        if subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode:
            run('git', 'commit', '-m', 'Discard rejected news; retain processed post IDs')
        # Record base ancestry without reintroducing rejected content or conflicts.
        run('git', 'merge', '-s', 'ours', '--no-edit', base)
    else:
        run('git', 'merge', '--no-edit', base)


if __name__ == '__main__':
    main()
