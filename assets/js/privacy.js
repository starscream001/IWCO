(function () {
    const key = 'iwco-statistics-v1';
    let started = false;
    function getChoice() { try { return localStorage.getItem(key); } catch (_) { return null; } }
    function startStatistics() {
        if (started) return;
        started = true;
        window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
        window.ym.l = Date.now();
        const script = document.createElement('script');
        script.src = 'https://mc.yandex.ru/metrika/tag.js';
        script.async = true;
        document.head.appendChild(script);
        // Session replay and automatic collection of form contents are disabled.
        window.ym(99721375, 'init', { clickmap: false, trackLinks: false, accurateTrackBounce: true, webvisor: false });
    }
    const banner = document.createElement('aside');
    banner.className = 'statistics-choice';
    banner.setAttribute('aria-label', 'Статистика посещений');
    banner.innerHTML = '<p>С вашего разрешения мы используем Яндекс Метрику для статистики посещений. Запись действий и содержимого формы отключена. <a href="/privacy.html">Подробнее об обработке данных</a>.</p><button type="button" data-choice="yes">Разрешить статистику</button><button type="button" data-choice="no">Без статистики</button>';
    banner.hidden = getChoice() !== null;
    document.body.appendChild(banner);
    if (getChoice() === 'yes') startStatistics();
    banner.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
        const choice = button.dataset.choice;
        try { localStorage.setItem(key, choice); } catch (_) { /* The choice applies for this visit. */ }
        banner.hidden = true;
        if (choice === 'yes') startStatistics();
        else if (started) window.location.reload();
    }));
    document.querySelectorAll('[data-statistics-settings]').forEach(button => button.addEventListener('click', () => {
        banner.hidden = false;
    }));
})();
