(function () {
    function loadVideos(article) {
        if (!article) return;
        article.querySelectorAll('.telegram-embed[data-telegram-post]').forEach(container => {
            if (container.dataset.loaded) return;
            container.dataset.loaded = 'true';
            const script = document.createElement('script');
            script.async = true;
            script.src = 'https://telegram.org/js/telegram-widget.js?22';
            script.setAttribute('data-telegram-post', container.dataset.telegramPost);
            script.setAttribute('data-width', '100%');
            container.appendChild(script);
        });
    }
    $(function () {
        const tabs = $('#tabs');
        tabs.on('tabsactivate', function (_event, ui) {
            loadVideos(ui.newPanel[0]);
        });
        loadVideos(document.querySelector('#news article:not([aria-hidden="true"])'));
    });
})();
