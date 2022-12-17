import sys
import logging
from time import sleep
from textwrap import dedent
from logging.handlers import RotatingFileHandler

import requests
import telegram
from environs import Env

logger = logging.getLogger(__file__)


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def start_bot(devman_token, bot, person_id):
    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {devman_token}'}
    params = None
    logger.info('Телеграм бот запущен\n')

    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            info_about_works_check = response.json()
            response_status = info_about_works_check.get('status')
            accepted_work = 'К сожалению, в работе нашлись ошибки.'
            not_accepted_work = dedent('''\
            Преподавателю всё понравилось,\
            можно приступать к следующему уроку!\
            ''')

            if response_status == 'found':
                params = {
                    'timestamp': info_about_works_check.get(
                        'last_attempt_timestamp')
                }
                new_attempt = info_about_works_check.get('new_attempts')[0]
                lesson_title = new_attempt.get('lesson_title')
                lesson_url = new_attempt.get('lesson_url')
                lesson_check = new_attempt.get('is_negative')

                message = dedent(f'''\
                У вас проверили работу "{lesson_title}"
                {accepted_work if lesson_check else not_accepted_work}
                Ссылка на урок: {lesson_url}
                ''')
            else:
                params = {
                    'timestamp': info_about_works_check.get(
                        'timestamp_to_request')
                }
                message = None
            if message:
                bot.send_message(chat_id=person_id, text=message)

        except requests.exceptions.ReadTimeout as read_timeout:
            logger.warning(f'Превышено время ожидания\n{read_timeout}\n')
        except requests.exceptions.ConnectionError as connect_error:
            logger.warning(f'Произошёл сетевой сбой\n{connect_error}\n')
            sleep(20)


def main():
    env = Env()
    env.read_env()
    devman_token = env.str('DEVMAN_TOKEN')
    telegram_token = env.str('CHECKED_WORK_TELEGRAM_TOKEN')
    person_id = env.str('PERSON_ID')

    bot = telegram.Bot(telegram_token)
    logging.basicConfig(
        filename='app.log',
        filemode='w',
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(asctime)s - %(message)s'
    )
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('app.log', maxBytes=15000, backupCount=2)
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    logger.addHandler(TelegramLogsHandler(bot, person_id))

    start_bot(devman_token, bot, person_id)


if __name__ == '__main__':
    main()
