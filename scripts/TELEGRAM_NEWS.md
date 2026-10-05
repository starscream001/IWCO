# News automation

Sources: public channels listed in `data/telegram-channels.json`; currently
`iwcowingchun`. No Telegram administrator permission is required.

The archive from 6 May 2026 through 2 October 2026 is imported manually:
26 channel messages became 16 stories with edited titles. Full post descriptions
are stored in the archive and rendered directly as local HTML. Related video
links were combined. Each story keeps its source links and publication date.
Original archive entries are in `data/news-archive.json`; rendered tabs are in
`news.html`. Old site news remains in place.

`data/telegram-web-news.json` records ID 432 as the imported channel watermark.
The daily importer adds only subsequent posts; no new posts means no new tabs,
no publication PR and no Telegram notification. Repeated runs don't duplicate
stories. New channels each get their own watermark; when adding a new channel,
the first run starts tracking at its current latest post, without importing its archive.
To add a public channel, add its username without @ to `data/telegram-channels.json`.
Edits and deletions of already imported posts require editorial review.

GitHub Actions runs daily at 10:43 Moscow, with a manual Run workflow option.
One open `codex/telegram-news` PR accumulates unpublished news. Photos are stored
locally. All news text is rendered as local HTML in news.html. Videos are direct
Telegram links; full Telegram posts and their captions are not embedded.

GitHub Actions secrets:
- TELEGRAM_BOT_TOKEN: bot token for PR notifications only.
- TELEGRAM_CHAT_ID: recipient ID (642040616).

Allow GitHub Actions to create pull requests under Settings → Actions → General
→ Workflow permissions. In Actions → Telegram news, Run workflow verifies import.
Do not automatically delete codex/telegram-news after merge: it holds pending state.
A closed unmerged PR is recreated on the next run. Resolve any merge conflict in
that branch before running again. Public repositories may disable scheduled runs
after 60 days without activity; watch workflow status during long quiet periods.

Telegram may change its web markup; parser failures stop the run without advancing
the committed watermark. The importer walks older pages back to the watermark.
It supports Telegram photos, text formatting and native videos; documents are skipped.

The contact form has a separate backend; see `contact-service/README.md`.
GitHub secrets are never embedded into client HTML or JavaScript.


Each publication also has a static URL under news/. site_pages.py generates
article metadata and sitemap.xml. The tabs page keeps the latest 20 entries;
older articles remain available through paginated archive pages (20 per page).
The importer updates article URLs, archives and sitemap whenever it adds posts.
