/* Local news selection with shareable URLs and native keyboard navigation. */
(function () {
  'use strict';
  const root = document.querySelector('#news #tabs');
  if (!root) return;
  const links = Array.from(root.querySelectorAll(':scope > .col-lg-4 > ul > li > a'));
  const articles = Array.from(root.querySelectorAll('.tabs-content > article'));
  const list = root.querySelector(':scope > .col-lg-4 > ul');
  list.setAttribute('aria-label', 'Выберите новость');
  function select(hash, scroll) {
    const current = articles.find(article => '#' + article.id === hash) || articles[0];
    if (!current) return;
    articles.forEach(article => { article.hidden = article !== current; });
    links.forEach(link => {
      if (link.hash === '#' + current.id) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    if (scroll && window.matchMedia('(max-width: 991px)').matches) {
      current.setAttribute('tabindex', '-1');
      current.focus({preventScroll: true});
      current.scrollIntoView({block: 'start'});
    }
  }
  links.forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    history.pushState(null, '', link.hash);
    select(link.hash, true);
  }));
  window.addEventListener('popstate', () => select(location.hash, false));
  window.addEventListener('hashchange', () => select(location.hash, false));
  select(location.hash, false);
})();
