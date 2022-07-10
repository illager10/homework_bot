import os
import time
import telegram
import requests
import logging

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from http import HTTPStatus


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)

log_format = "%(asctime)s - [%(levelname)s] - %(message)s"
handler.setFormatter(logging.Formatter(log_format))

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
# ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statues/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Cообщение отправлено успешно')
    except Exception as error:
        logger.error(f'Возникла ошибка при отправке сообщения{error}')


def get_api_answer(current_timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В случае успешного запроса должна вернуть ответ API.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            try:
                return response.json()
            except Exception as error:
                logger.error(
                    'Ошибка преобразования из формата json к типам данных'
                    f'python: {error}'
                )
        else:
            logger.error(f'API возвращает код: {response.status_code}.')
            raise AssertionError
    except Exception as error:
        logger.error(f'Возникла ошибка при запросе к эндпоинту{error}')
        raise AssertionError


def check_response(response):
    """
    Проверяет ответ API на корректность.
    Функция должна вернуть список домашних работ.
    """
    if type(response) is not dict:
        logger.error('Тип данных ответа API не является словарём')
        raise TypeError

    if ('homeworks' not in response) or ('current_date' not in response):
        logger.error('Ответ API не содержит необходимых ключей')
        raise KeyError

    if type(response.get('homeworks')) is not list:
        logger.error('Домашние работы ответа API не являются списком')
        raise TypeError

    return response.get('homeworks')


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе
     статус этой работы.
    """
    if not homework:
        logger.error('Информация о домашней работе - пустой список')
        raise ValueError
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.error(
            'Нет доступа к переменным окружения или их значения отсутствуют'
        )
        raise ValueError

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Новый статус отсутствует')

            current_timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
