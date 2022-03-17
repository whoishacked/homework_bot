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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise Exception(f'Не удалось отправить сообщение: {error}')


def get_api_answer(current_timestamp):
    """Sends request to API end-point."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    header_params = {'headers': HEADERS, 'params': params}
    try:
        response = requests.get(ENDPOINT, **header_params)
    except Exception as error:
        raise Exception(f'Ошибка соединения с енд-поинт: {error}')
    if response.status_code != HTTPStatus.OK:
        raise APIStatusesException(f'Неверный код ответа от API: '
                                   f'{response.status_code}')
    try:
        response = response.json()
    except ValueError:
        raise
    return response


def check_response(response):
    """Checks API answer & return homeworks."""
    try:
        homeworks = response['homeworks']
        current_date = response['current_date']
    except KeyError:
        raise
    if homeworks and isinstance(homeworks, Dict):
        raise HomeWorkTypeError('Под ключем homeworks не словарь')
    return homeworks


def parse_status(homework):
    """Extracts homework's information & status."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError:
        raise
    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeWorkStatusesException('Статус не соответствует '
                                        'ожидаемому')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checks API tokens."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    try:
        if not all(tokens):
            raise TokenError(f'Не удалось получить токен')
    except TokenError:
        return False
    return True


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except Exception as error:
        logger.critical(error)
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
                    logger.info('Отправка сообщения в telegram')
                    send_message(bot, message)
                    logger.info('Сообщение отправлено')
                    last_message = message
            else:
                logger.debug(f'Новых статусов нет. Перепроверка через '
                             f'{RETRY_TIME} сек.')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_message != message:
                logger.info('Отправка сообщения в telegram')
                send_message(bot, message)
                logger.info('Сообщение отправлено')
                last_message = message
        else:
            logger.debug('Отправка повторного запроса после таймаута')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
