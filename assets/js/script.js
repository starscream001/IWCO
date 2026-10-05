const CONTACT_API = 'https://185.149.144.209';
const contactForm = document.getElementById('contact');
let contactChallenge = '';
let contactChallengeTime = 0;
let challengeRequest = null;
let contactSubmitting = false;

async function refreshContactChallenge() {
    if (challengeRequest) return challengeRequest;
    challengeRequest = (async () => {
        const response = await fetch(`${CONTACT_API}/api/challenge`, {
            cache: 'no-store', signal: AbortSignal.timeout(10000)
        });
        if (!response.ok) throw new Error('Не удалось подключиться. Попробуйте позже или позвоните нам.');
        const data = await response.json();
        contactChallenge = data.challenge;
        contactChallengeTime = Date.now();
    })();
    try {
        await challengeRequest;
    } finally {
        challengeRequest = null;
    }
}

async function submitForm(event) {
    event.preventDefault();
    if (contactSubmitting) return false;
    const form = event.target;
    if (!form.reportValidity()) return false;
    contactSubmitting = true;
    const button = form.querySelector('button[type="submit"]');
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Отправляем…';
    try {
        if (!contactChallenge || Date.now() - contactChallengeTime > 25 * 60 * 1000) {
            await refreshContactChallenge();
        }
        // Allow the server's minimum form-filling interval after a fresh challenge.
        const wait = 2200 - (Date.now() - contactChallengeTime);
        if (wait > 0) await new Promise(resolve => setTimeout(resolve, wait));
        const values = new FormData(form);
        const response = await fetch(`${CONTACT_API}/api/contact`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: values.get('name'), phone: values.get('phone'),
                hall: values.get('hall'), message: values.get('message'),
                website: values.get('website') || '', challenge: contactChallenge
            }),
            signal: AbortSignal.timeout(20000)
        });
        let data = {};
        try { data = await response.json(); } catch (_) { /* Nginx may return HTML errors. */ }
        if (!response.ok || data.ok !== true) {
            throw new Error(response.status === 429
                ? 'Слишком много заявок. Подождите несколько минут или позвоните нам.'
                : (data.error || 'Не удалось отправить заявку. Попробуйте позже или позвоните нам.'));
        }
        form.reset();
        alert('Заявка отправлена! Мы свяжемся с вами.');
    } catch (error) {
        alert(error.name === 'TimeoutError' || error instanceof TypeError
            ? 'Нет ответа от сервера. Попробуйте позже или позвоните нам.'
            : error.message);
    } finally {
        contactChallenge = '';
        contactSubmitting = false;
        button.disabled = false;
        button.textContent = originalText;
        refreshContactChallenge().catch(() => {});
    }
    return false;
}

if (contactForm) {
    const honeypot = document.createElement('input');
    honeypot.type = 'text';
    honeypot.name = 'website';
    honeypot.tabIndex = -1;
    honeypot.autocomplete = 'off';
    honeypot.setAttribute('aria-hidden', 'true');
    honeypot.style.cssText = 'position:absolute;left:-10000px;width:1px;height:1px;';
    contactForm.appendChild(honeypot);
    refreshContactChallenge().catch(() => {});
}
