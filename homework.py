import logging
import os
import random
import sys
import time
from http import HTTPStatus
from logging import Formatter, StreamHandler

import requests
from dotenv import load_dotenv
from telegram import Bot, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_Y')
TELEGRAM_TOKEN = os.getenv('TOKEN_T')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

# Original
# RETRY_TIME = 600
# Debug version
RETRY_TIME = 30


ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

BOTS_REPLICAS = [
    'Себе тыкни! Начинка для гробов!',
    '404! Свободен! Джим Бим лучше мне подготовь.',
    'Я от тебя другого и не ждал.',
    'Не мешай мне, кожаный мешок.',
    'Bite my shiny metal ass.',
    'Пиво рулит, не ты!',
]

STICKERS = {
    '1':
    'CAACAgIAAxkBAAED8JpiC' 
    + '-NT140boOujnrJnLwZCDxRehgACRQwAAnqdmEo2Geh166RTLCME',
    '2':
    'CAACAgIAAxkBAAED8JxiC-TR1-6VWQ'
    + 'aY5pta3xfRBB1zJQACoAwAAttxQEoPLS2JLnzifSME',
    '3':
    'CAACAgIAAxkBAAED8J5iC-UapCEYA'
    + 'AHaj-kb_-r5gH2n0vsAArIAA61lvBRB3wABZwq4QhkjBA',
}

PICTURES = {
    'ben_start': 'img/ben_start.png',
    'ben_end': 'img/ben_end.png',
    'ben_msg': 'img/ben_msg.png',
    'ben_result': 'img/ben_result.png',
    'ben_bot': 'img/ben_bot.png',
    'ben_error': 'img/ben_error.png',
}

# Переменная-флаг SEARCH_POINT нужна работы кнопок start, stop
SEARCH_POINT = True
# Переменная-флаг FOUND_WORK нужна для смены ответа
# при повторном нажатии на кнопки.
FOUND_WORK = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(levelname)s-%(message)s'
)

# Создаем логер и используем хендлер для потока
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# handler = StreamHandler(stream=None)
# Formatter = logging.Formatter(
#     '%(asctime)s-%(levelname)s-%(message)s'
# )
# handler.setFormatter(Formatter)
# logger.addHandler(handler)


def send_message(bot, message: str):
    """Бот отправляет сообщение и стикер."""
    try:
        img = open(PICTURES['ben_result'], 'rb')
        bot.send_photo(TELEGRAM_CHAT_ID, img)
        logging.info('Картинка отправлена.')
    except Exception:
        logging.error('Картинка не отправлена!')

    msg = """Как и многие жизненные проблемы,
    эту можно решить сгибанием.
    Держи ответ!: """

    bot.send_message(TELEGRAM_CHAT_ID, msg)
    logging.info('Сообщение отправлено!')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Сообщение отправлено!')

    # Стикеры подогнаны под запрет не более двух аргументов на вход
    try:
        if 'Ура!' in message:
            msg_bot = STICKERS['1']
        elif 'взята' in message:
            msg_bot = STICKERS['2']
        elif 'замечания' in message:
            msg_bot = STICKERS['3']
        bot.send_sticker(TELEGRAM_CHAT_ID, msg_bot)
    except Exception:
        logging.error('Стикеры не найдены!')
        raise Exception


def send_error_message(bot, message: str):
    """Бот сообщает об ошибке."""
    try:
        img = open(PICTURES['ben_result'], 'rb')
        bot.send_photo(TELEGRAM_CHAT_ID, img)
        logging.info('Картинка отправлена.')
    except Exception:
        logging.error('Картинка не отправлена!')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Сообщение отправлено!')


# ПОИСК
def get_api_answer(current_timestamp: int) -> str:
    """Получаем ответ на последнюю домашку по точке из пулинга."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != HTTPStatus.OK:
            msg = 'Ошибка в доступе к Практикуму.'
            logging.error(msg)
            raise Exception(msg)
        else:
            return response.json()
    except Exception as error:
        msg = f'Ошибка в запросе к Практикуму: {error}'
        logging.error(msg)
        raise Exception(msg)


def check_response(response):
    """Проверяем есть ли что в словаре(списке)."""
    empty_dict = {}
    try:
        if isinstance(response, dict):
            test_list = response.get('homeworks')
        # else:
        #     logging.info('Response - список, а не словарь.')
        #     test_list = response[0].get('homeworks')
            if len(test_list) > 1:
                if 'homework_name' in test_list[0] or 'status' in test_list[0]:
                    return test_list[0]
                else:
                    msg = 'Нет ключа: homework_name или status'
                    logging.error(msg)
                    raise KeyError(msg)
            else:
                return test_list
        else:
            raise TypeError('Некорректный тип responce.')    
    except KeyError:
        msg = 'Нет ключа homeworks.'
        logging.error(test_list)
        logging.error(msg)
        raise KeyError(msg)
    except TypeError:
        msg = 'Некорректный тип данных.'
        logging.error(msg)
        raise TypeError(msg)


def parse_status(homework: dict) -> str:
    """Формируем сообщение, если доступны все данные."""
    try:
        if len(homework)> 0:
            if not isinstance(homework, dict):
                msg = 'homework не словарь'
                logging.error(msg)
                print(homework)
                raise Exception(msg)
            if not'status'in homework:
                raise KeyError('status нет в homework')
            homework_status = homework.get('status')
            if not homework_status in HOMEWORK_STATUSES:
                raise KeyError(
                            f'{homework_status} нет в HOMEWORK_STATUSES.'
                        )
            verdict = HOMEWORK_STATUSES[homework_status]
            if 'homework_name' in homework:
                    homework_name = homework.get('homework_name')
                    msg = (
                        f'Изменился статус проверки работы "{homework_name}"'
                        f'.{verdict}'
                    )
                    return msg
            return f'{verdict}'
        else:
            return ''
    except KeyError as msg:
        raise KeyError(msg)
    except Exception as msg:
        raise Exception(msg)


def check_tokens() -> bool:
    """Если все токены в наличии, то Трушечка."""
    if not TELEGRAM_CHAT_ID or not TELEGRAM_TOKEN or not PRACTICUM_TOKEN:
        return False
    return True


# /ПОИСК
def say_answer(update, context):
    """Вопросы тут пока не к месту."""
    try:
        img = open(PICTURES['ben_msg'], 'rb')
    except Exception:
        logging.error('Картинка не найдена!')
    text_bot = random.choice(BOTS_REPLICAS)
    chat_from_leather_bag = update.effective_chat
    try:
        context.bot.send_photo(
            chat_from_leather_bag.id,
            img
        )
        logging.info('Картинка отправлена.')
    except Exception:
        logging.error('Картинка не отправлена!')

    context.bot.send_message(
        chat_from_leather_bag.id,
        text=text_bot
    )
    logging.info('Сообщение отправлено!')


def wake_up(update, context):
    """Приветствие при запуске бота."""
    try:
        img = open(PICTURES['ben_bot'], 'rb')
    except Exception:
        logging.error('Картинка не найдена!')
    chat_from_leather_bag = update.effective_chat
    if chat_from_leather_bag.id != int(TELEGRAM_CHAT_ID):
        try:
            context.bot.send_photo(
                chat_from_leather_bag.id,
                img
            )
            logging.info('Картинка отправлена.')
        except Exception:
            logging.info('Картинка не отправлена!')
        context.bot.send_message(
            chat_from_leather_bag.id,
            text='Извини чувак, но я тебя не знаю!'
        )
        logging.info('Сообщение отправлено!')
    else:
        leather_bag_name = update.message.chat.first_name
        text_bot = (
            f"Ну что {leather_bag_name} - начинка для гробов!"
            "Посмотрим, что у нас получится!"
        )
        button = ReplyKeyboardMarkup(
            [['/search'], ['/stop']], resize_keyboard=True
        )
        try:
            context.bot.send_photo(
                chat_from_leather_bag.id,
                img
            )
            logging.info('Картинка отправлена.')
        except Exception:
            logging.error('Картинка не отправлена!')
        context.bot.send_message(
            chat_from_leather_bag.id,
            text=text_bot,
            reply_markup=button
        )
        logging.info('Сообщение отправлено!')


# Метки кнопок
def start_search(update, context):
    """Начинаем поиск и выводим оповещение об этом."""
    global SEARCH_POINT
    try:
        img = open(PICTURES['ben_start'], 'rb')
    except Exception:
        logging.error('Картинка не найдена!')
    messages = [
    'Иду за Джеком, будет желание - гляну, есть ли что для тебя.',
    'Ты уже тыкал сюда, придумай что-нибудь получше.'
    ]
    chat = update.effective_chat
    if SEARCH_POINT:
        msg_bot = messages[0]
    else:
        msg_bot = messages[1]
    try:
        context.bot.send_photo(chat.id, img)
        logging.info('Картинка отправлена.')
    except Exception:
        logging.error('Картинка не отправлена!')
    if chat.id != int(TELEGRAM_CHAT_ID):
        context.bot.send_message(chat.id, 'Чувак, не делай так больше!')
        logging.info('Сообщение отправлено!')
    else:
        context.bot.send_message(chat.id, msg_bot)
        logging.info('Сообщение отправлено!')
        SEARCH_POINT = False


def stop_search(update, context):
    """Завершаем поиск и выводим оповещение об этом."""
    global SEARCH_POINT
    global FOUND_WORK
    try:
        img = open(PICTURES['ben_end'], 'rb')
    except Exception:
        logging.error('Картинка не найдена!')
    messages = [
    'Я и не искал.',
    'Ты уже тыкал сюда, придумай что-нибудь получше.',
    'Должен будешь!'
    ]
    chat = update.effective_chat
    if not SEARCH_POINT:
        if not FOUND_WORK:
            msg_bot = messages[0]
        else:
            msg_bot = messages[2]
            FOUND_WORK = False
    else:
        msg_bot = messages[1]
    try:
        context.bot.send_photo(chat.id, img)
        logging.info('Картинка отправлена.')
    except Exception:
        logging.error('Картинка не отправлена!')
    if chat.id != int(TELEGRAM_CHAT_ID):
        context.bot.send_message(chat.id, 'Чувак, не делай так больше!')
        logging.info('Сообщение отправлено!')
    else:
        context.bot.send_message(chat.id, msg_bot)
        logging.info('Сообщение отправлено!')
        SEARCH_POINT = True


def main():
    """Основная логика работы бота."""
    global FOUND_WORK
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        updater = Updater(token=TELEGRAM_TOKEN)
        # Debug version
        current_timestamp = int(time.time()) - 2996000
        # Original
        # current_timestamp = int(time.time())
        updater.dispatcher.add_handler(
            CommandHandler('start', wake_up)
        )
        updater.dispatcher.add_handler(
            CommandHandler('search', start_search)
        )
        updater.dispatcher.add_handler(
            CommandHandler('stop', stop_search)
        )
        updater.dispatcher.add_handler(
            MessageHandler(Filters.text, say_answer)
        )
        updater.dispatcher.add_handler(
            MessageHandler(
                Filters.chat(chat_id=TELEGRAM_CHAT_ID),
                get_api_answer
            )
        )
        updater.start_polling()
        try:
            while True:
                if not SEARCH_POINT:
                    try:
                        time_marker = {'from_date': f'{current_timestamp}'}
                        response = requests.get(
                            ENDPOINT,
                            headers=HEADERS,
                            params=time_marker
                        )
                        # logging.info(f'{current_timestamp}')
                        message = get_api_answer(current_timestamp)
                        answer = check_response(message)
                        result = parse_status(answer)
                        if result and len(result) > 0:
                            send_message(bot, result)
                            logging.info('Сообщение отправлено.')
                            FOUND_WORK = True
                        current_timestamp = response.json().get(
                            'current_date'
                        )
                        time.sleep(RETRY_TIME)
                        # logging.info(f'{current_timestamp}')
                    # except IndexError:
                    #     logging.info('Ответа пока нет.')
                    except Exception as error:
                        message = f'Дангер! Паник!: {error}'
                        logging.critical(message)
                        send_error_message(bot, message)
                        current_timestamp = int(time.time())

        except KeyboardInterrupt:
            updater.idle()
    else:
        logging.critical('Токены всё, тю-тю...')
        sys.exit(1)


if __name__ == '__main__':
    main()
