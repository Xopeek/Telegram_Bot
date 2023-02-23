import logging
import os
import sys
import time
from http import HTTPStatus

import requests

from dotenv import load_dotenv
import telegram

from exceptions import InvalidApi, InvalidResponse, EmptyList


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    logger.debug('Попытка отправки сообщения в Telegram')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(f'Бот не может отправить сообщение {error}')


def get_api_answer(timestamp):
    """Отправка запроса к эндпоинту API и возврат ответа API."""
    payload = {'from_date': timestamp}
    logger.debug('Попытка запроса к эндпоинту API')
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except (requests.exceptions.RequestException, Exception) as error:
        raise InvalidApi(f'Ошибка подключения к API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise InvalidResponse('Код ответа не 200')
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError('В ответе API содержится не словарь')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise InvalidApi('Неправильный ответ API')
    if not isinstance(homeworks, list):
        raise TypeError('Ответ API не список')
    if not homeworks:
        raise EmptyList('Новые статусы отсутствуют')
    return homeworks


def parse_status(homework):
    """Проверяет статус работы и возвращает вердикт по домашки."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('homework_name не найден')
    if homework_status is None:
        raise KeyError('homework_status не найден')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'{homework_status}'
                       f' не найден в стандартных ответах')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = ''
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                if status != last_message:
                    send_message(bot, status)
                    last_message = status
            else:
                logger.debug('Домашка отсутствует')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.debug(message)
            if error != last_error:
                send_message(bot, message)
                last_error = error
        finally:
            logger.debug(f'Бот ожидает {RETRY_PERIOD} секунд')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
