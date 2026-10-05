# IWCO contact backend

Production endpoint: https://185.149.144.209/api/contact
Challenge endpoint: https://185.149.144.209/api/challenge
Health: https://185.149.144.209/healthz

The site stays on GitHub Pages. This backend runs on the Russian server in
`/opt/iwco-contact`, container `iwco-contact`, limited to 128 MB and 0.25 CPU.
It listens only on 127.0.0.1:18081; Nginx exposes the two API routes over HTTPS.
Docker image construction excludes secrets, private keys, certificates and state.

Secrets are root-readable `/opt/iwco-contact/secrets.env`:
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CHALLENGE_SECRET.
The new token was delivered encrypted from GitHub Actions using a temporary RSA
public key. The receiver verified the existing bot ID before accepting it.
The receiver, its HTTP route and private key were removed after provisioning.
Changing GitHub Secrets later does NOT automatically update the backend token.
To rotate, update the root-only env file over SSH and recreate the container.
Never copy tokens into this repository or the client JavaScript.

Nginx rate limits contact submission to two requests per minute per source IP
(with a small burst). Signed challenges expire in 30 minutes and can only be used
once. A honeypot rejects simple form bots. These controls reduce automated spam;
they do not claim to replace a CAPTCHA against determined attackers.
The app validates fields and sends Telegram messages with `parse_mode=HTML`.
User text is HTML-escaped; literal `<b>` entered by a visitor remains literal text.
No names, phones or messages are stored in server logs or the SQLite replay DB.

The Russian server cannot directly reach Telegram API. The independent systemd
service `iwco-telegram-egress` routes ONLY api.telegram.org through the existing
NL profile. It binds loopback and the Docker bridge, and refuses other targets.
HTTPS certificate verification remains enabled end to end.
Its private VPN configuration stays in `/opt/iwco-contact/telegram-egress.json`.
No existing VPN inbound or subscription configuration was edited.

Let's Encrypt IP certificate lives under `/etc/letsencrypt/live/iwco-contact-ip`.
`iwco-cert-renew.timer` checks renewal twice daily and reloads Nginx on renewal.
IP certificates last about six days; keep the timer enabled and port 80 available
for `/.well-known/acme-challenge/` in the IP-specific Nginx server block.
The existing `sub.ilyamanik.ru` server block is unchanged.
Backup of prior Nginx configuration: `/var/backups/iwco-contact/nginx-before`.

Update from this directory on the server:
`docker compose up -d --build`

Verification:
`python3 -m unittest discover -s contact-service -p 'test_*.py'`
Use real HTTPS/CORS checks and one explicitly labelled test message after deployment.
