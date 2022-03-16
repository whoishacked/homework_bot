import logging
import os
import sys
import time

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
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)


def send_message(bot, message):
    """Sends messages in telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f'Не удалось отправить сообщение в чат: {error}'
        logger.error(message)
    else:
        logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Sends request to API end-point."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise APIStatusesException(f'Неверный код ответа от API: '
                                   f'{response.status_code}')
    try:
        response = response.json()
    except ValueError as error:
        message = f'Не удалось получить json: {error}'
        logger.error(message)
    except APIStatusesException as error:
        logger.error(error)
    else:
        return response


def check_response(response):
    """Checks API answer & return homeworks."""
    homeworks = response['homeworks']
    try:
        if homeworks and type(homeworks[0]) != dict:
            print(type(homeworks[0]))
            raise HomeWorkTypeError('Под ключем homeworks не список')
    except HomeWorkTypeError as error:
        logger.error(error)
    return homeworks


def parse_status(homework):
    """Extracts homework's information & status."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        if homework_status not in HOMEWORK_STATUSES:
            raise HomeWorkStatusesException('Статус не соответствует '
                                            'ожидаемому')
    except HomeWorkStatusesException as error:
        logger.error(error)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checks API tokens."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    try:
        for token in tokens:
            if not tokens[token]:
                raise TokenError(f'Не удалось получить {token}')
    except TokenError as error:
        logger.critical(error)
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
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
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
            time.sleep(RETRY_TIME)
        else:
            logger.debug('Отправка повторного запроса после таймаута')


if __name__ == '__main__':
    main()
