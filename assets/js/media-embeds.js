document.addEventListener('click', (event) => {
    const button = event.target.closest('.media-play');
    if (!button) return;
    const card = button.closest('.media-embed');
    const stage = card.querySelector('.media-stage');
    if (card.dataset.provider === 'rutube') {
        let source;
        try { source = new URL(card.dataset.mediaSrc); } catch (_) { return; }
        if (source.origin !== 'https://rutube.ru' || !/^\/play\/embed\/[a-f0-9]{32}$/.test(source.pathname)) return;
        const frame = document.createElement('iframe');
        frame.src = source.href;
        frame.title = 'Видео Rutube';
        frame.allow = 'encrypted-media; fullscreen; picture-in-picture';
        frame.allowFullscreen = true;
        frame.referrerPolicy = 'strict-origin-when-cross-origin';
        stage.replaceChildren(frame);
    } else if (card.dataset.provider === 'telegram') {
        if (!/^[a-zA-Z][a-zA-Z0-9_]{3,31}\/[1-9]\d{0,12}$/.test(card.dataset.mediaSrc)) return;
        const script = document.createElement('script');
        script.src = 'https://telegram.org/js/telegram-widget.js?22';
        script.async = true;
        script.dataset.telegramPost = card.dataset.mediaSrc;
        script.dataset.width = '100%';
        script.dataset.userpic = 'false';
        stage.replaceChildren(script);
        card.classList.add('is-loaded');
    }
});
