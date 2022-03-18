import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (APIStatusesException, HomeWorkStatusesException,
                        HomeWorkTypeError, TokenError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s '
                              '%(lineno)d %(message)s')
handler.setFormatter(formatter)


def send_message(bot, message):
    """Sends messages in telegram chat."""
    logger.info('Отправка сообщения в telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise Exception(f'Не удалось отправить сообщение: {error}')
    else:
        logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Sends request to API end-point."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    header_params = {'headers': HEADERS, 'params': params}
    try:
        response = requests.get(ENDPOINT, **header_params)
    except Exception as error:
        raise Exception(f'Ошибка соединения с енд-поинт: {error}, '
                        f'параметры: {header_params}')
    if response.status_code != HTTPStatus.OK:
        raise APIStatusesException(f'Неверный код ответа от API: '
                                   f'{response.status_code}')
    try:
        response = response.json()
    except Exception as error:
        raise Exception(f'Ошибка получения json: {error}')
    return response


def check_response(response):
    """Checks API answer & return homeworks."""
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутсвуют нужные ключи в response')
    homeworks = response['homeworks']
    if isinstance(homeworks, Dict):
        raise HomeWorkTypeError('Под ключем homeworks не dict')
    return homeworks


def parse_status(homework):
    """Extracts homework's information & status."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Отсутсвуют нужные ключи в homework')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeWorkStatusesException('Статус не соответствует '
                                        'ожидаемому')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checks API tokens."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Один из токенов недоступен. Завершение работы.')
        sys.exit(0)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
            else:
                logger.debug(f'Новых статусов нет. Перепроверка через '
                             f'{RETRY_TIME} сек.')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
        else:
            logger.debug('Отправка повторного запроса после таймаута')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
