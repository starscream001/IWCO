
// Функция для отправки данных в Telegram-бота
async function sendTelegramMessage(token, chatId, message) {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    try {
        await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: chatId,
                text: message
            })
        });
        console.log('Сообщение успешно отправлено');
    } catch (error) {
        console.error('Ошибка при отправке сообщения:', error);
    }
}

// Функция для обработки отправки формы
function submitForm(event) {
    event.preventDefault();

    // Получаем значения полей формы
    const formData = new FormData(event.target);
    const name = formData.get('name');
    const phone = formData.get('phone');
    const hall = formData.get('hall');
    const message = formData.get('message');

    // Формируем сообщение для отправки
    const telegramMessage = `
Имя: ${name}
Телефон: ${phone}
Зал: ${hall}
Сообщение: ${message}
    `.trim();

    // Токен вашего бота и chat_id
    const botToken = '6792043729:AAG7cPguS2m4Io0KWfj7yh-hjnXeqQOC3Ao';
    const chatId = '642040616';

    // Отправляем сообщение в Telegram
    sendTelegramMessage(botToken, chatId, telegramMessage)
        .then(() => alert('Сообщение успешно отправлено!'))
        .catch((error) => alert(`Произошла ошибка при отправке сообщения: ${error.message}`));
}

// Подключаемся к событию отправки формы
document.getElementById('contact').addEventListener('submit', submitForm);