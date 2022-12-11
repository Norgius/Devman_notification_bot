import sys
import logging
import argparse
from time import sleep
from logging.handlers import RotatingFileHandler

import requests
import telegram
from environs import Env

logger = logging.getLogger(__file__)


def parse_response(response):
    response_json = response.json()
    response_status = response_json.get('status')
    accepted_work = 'К сожалению, в работе нашлись ошибки.'
    not_accepted_work = 'Преподавателю всё понравилось, ' \
                        'можно приступать к следующему уроку!'
    if response_status == 'found':
        params = {'timestamp': response_json.get('last_attempt_timestamp')}
        new_attempt = response_json.get('new_attempts')[0]
        lesson_title = new_attempt.get('lesson_title')
        lesson_url = new_attempt.get('lesson_url')
        lesson_check = new_attempt.get('is_negative')

        message = f'У вас проверили работу "{lesson_title}"\n\n'\
                  f'{accepted_work if lesson_check else not_accepted_work}\n'\
                  f'Ссылка на урок: {lesson_url}'
        return params, message
    else:
        params = {'timestamp': response_json.get('timestamp_to_request')}
        return params, None


def start_bot(devman_token, telegram_token, person_id):
    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {devman_token}'}
    params = None
    bot = telegram.Bot(telegram_token)
    logger.info('Телеграм бот запущен')
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            params, message = parse_response(response)
            if message:
                bot.send_message(chat_id=person_id, text=message)
        except requests.exceptions.ReadTimeout as read_timeout:
            logger.warning(f'Превышено время ожидания\n{read_timeout}\n')
            sys.stderr.write(f'Превышено время ожидания\n{read_timeout}\n\n')
        except requests.exceptions.ConnectionError as connect_error:
            logger.warning(f'Произошёл сетевой сбой\n{connect_error}\n')
            sys.stderr.write(f'Произошёл сетевой сбой\n{connect_error}\n\n')
            sleep(20)


def main():
    logging.basicConfig(
        filename='app.log',
        filemode='w',
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(asctime)s - %(message)s'
    )
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('app.log', maxBytes=15000, backupCount=2)
    logger.addHandler(handler)

    parser = argparse.ArgumentParser(
        description='Укажите ваш телеграм id, узнать его можно по ссылке:' \
                    'https://telegram.me/userinfobot'
    )
    parser.add_argument('id', type=int, help='телеграм id')
    args = parser.parse_args()

    env = Env()
    env.read_env()
    devman_token = env.str('DEVMAN_TOKEN')
    telegram_token = env.str('CHECKED_WORK_TELEGRAM_TOKEN')
    start_bot(devman_token, telegram_token, args.id)


if __name__ == '__main__':
    main()
