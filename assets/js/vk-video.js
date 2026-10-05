document.addEventListener('click', (event) => {
    const button = event.target.closest('.vk-video-play');
    if (!button) return;
    const card = button.closest('.vk-video');
    let source;
    try { source = new URL(card.dataset.vkSrc); } catch (_) { return; }
    if (source.origin !== 'https://vkvideo.ru' || source.pathname !== '/video_ext.php') return;
    const frame = document.createElement('iframe');
    frame.src = source.href;
    frame.title = 'Видео ВКонтакте';
    frame.allow = 'encrypted-media; fullscreen; picture-in-picture; screen-wake-lock';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    card.querySelector('.vk-video-stage').replaceChildren(frame);
});
