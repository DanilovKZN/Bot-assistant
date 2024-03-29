import logging
import os
import random
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.error import TelegramError

load_dotenv()
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')


BOTS_REPLICAS = [
    'Себе тыкни! Начинка для гробов!',
    '404! Свободен! Джим Бим лучше мне подготовь.',
    'Я от тебя другого и не ждал.',
    'Не мешай мне, кожаный мешок.',
    'Bite my shiny metal ass.',
    'Пиво рулит, не ты!',
]

STICKERS = {
    # Работа прошла (100%)
    'Выполнено':
    'CAACAgIAAxkBAAED8JpiC'
    + '-NT140boOujnrJnLwZCDxRehgACRQwAAnqdmEo2Geh166RTLCME',
    # Работа дошла, но не проверена (Зевает)
    'Не проверено':
    'CAACAgIAAxkBAAED8JxiC-TR1-6VWQ'
    + 'aY5pta3xfRBB1zJQACoAwAAttxQEoPLS2JLnzifSME',
    # Работа требует доработок (Стучит по клаве)
    'Доработай':
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


# Пристанище флагов
class MainFlags:
    """Флаги для выполнения кнопок и выбора ответа"""
    result_while = True
    result_answer = False
    result_bad = True

    def changing_result_w(self, result_w: bool):
        if isinstance(result_w, bool):
            MainFlags.result_while = result_w
        else:
            msg = f'Неверный тип флага {result_w}!'
            logger.error(msg)
            logging.error(msg)
            raise TelegramError(msg)

    def changing_result_a(self, result_a: bool):
        if isinstance(result_a, bool):
            MainFlags.result_while = result_a
        else:
            msg = f'Неверный тип флага {result_a}!'
            logger.error(msg)
            logging.error(msg)
            raise TelegramError(msg)

    def changing_result_bad(self, result_bad: bool):
        if isinstance(result_bad, bool):
            MainFlags.result_bad = result_bad
        else:
            msg = f'Неверный тип флага {result_bad}!'
            logger.error(msg)
            logging.error(msg)
            raise TelegramError(msg)        


# Создаем логер и используем хендлер для записи в файл
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'lags.log',
    maxBytes=50_000_000,
    backupCount=5
)
logger.addHandler(handler)


# Ответы на вопросы
def say_answer(update, context):
    """Вопросы тут пока не к месту."""
    try:
        img = open(PICTURES['ben_msg'], 'rb')
    except TelegramError:
        logger.error('Картинка не найдена!')
    text_bot = random.choice(BOTS_REPLICAS)
    chat_from_leather_bag = update.effective_chat
    context.bot.send_photo(
        chat_from_leather_bag.id,
        img
    )
    logger.info('Картинка отправлена.')
    logging.info('Картинка отправлена.')
    context.bot.send_message(
        chat_from_leather_bag.id,
        text=text_bot
    )
    logger.info('Сообщение отправлено!')
    logging.info('Сообщение отправлено!')


# Активация бота
def wake_up(update, context):
    """Приветствие при запуске бота."""
    try:
        img = open(PICTURES['ben_bot'], 'rb')
    except TelegramError:
        logger.error('Картинка не найдена!')
    chat_from_leather_bag = update.effective_chat
    if chat_from_leather_bag.id != int(TELEGRAM_CHAT_ID):
        context.bot.send_photo(
            chat_from_leather_bag.id,
            img
        )
        logger.info('Картинка отправлена.')
        context.bot.send_message(
            chat_from_leather_bag.id,
            text='Извини чувак, но я тебя не знаю!'
        )
        logger.info('Сообщение отправлено!')
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
        context.bot.send_photo(
            chat_from_leather_bag.id,
            img
        )
        logger.info('Картинка отправлена.')
        context.bot.send_message(
            chat_from_leather_bag.id,
            text=text_bot,
            reply_markup=button
        )
        logger.info('Сообщение отправлено!')
        logging.info('Сообщение отправлено!')

# Отправка бага
def send_error_message(bot, message: str): 
    """Бот сообщает об ошибке."""
    flag = MainFlags()
    try: 
        img = open(PICTURES['ben_error'], 'rb') 
        bot.send_photo(TELEGRAM_CHAT_ID, img)
        logging.info('Картинка отправлена.') 
    except TelegramError:
        logging.error('Картинка не отправлена!')
    bot.send_message(TELEGRAM_CHAT_ID, message) 
    logging.info('Сообщение отправлено!')
    flag.changing_result_bad(False)


# Метки кнопок бота
def start_search(update, context):
    """Начинаем поиск и выводим оповещение об этом."""
    flag = MainFlags()
    try:
        img = open(PICTURES['ben_start'], 'rb')
    except TelegramError:
        logger.error('Картинка не найдена!')
    messages = [
        'Иду за Джеком, будет желание - гляну есть ли что для тебя.',
        'Ты уже тыкал сюда, придумай что-нибудь получше.',
        'Я сломан и отказываюсь искать что-либо, тем более для тебя!'
    ]
    chat = update.effective_chat
    if flag.result_while:    
        msg_bot = messages[0]
    else:
        msg_bot = messages[1]
    if not flag.result_bad:
        msg_bot = messages[2] 
    context.bot.send_photo(chat.id, img)
    logger.info('Картинка отправлена.')
    if chat.id != int(TELEGRAM_CHAT_ID):
        context.bot.send_message(chat.id, 'Чувак, не делай так больше!')
        logger.info('Сообщение отправлено!')
    else:
        context.bot.send_message(chat.id, msg_bot)
        logger.info('Сообщение отправлено!')
        logging.info('Сообщение отправлено!')
        flag.changing_result_w(False)


def stop_search(update, context):
    """Завершаем поиск и выводим оповещение об этом."""
    flag = MainFlags()
    try:
        img = open(PICTURES['ben_end'], 'rb')
    except TelegramError:
        logger.error('Картинка не найдена!')
    messages = [
        'Я и не искал.',
        'Ты уже тыкал сюда, придумай что-нибудь получше.',
        'Должен будешь!'
    ]
    chat = update.effective_chat
    if not flag.result_while:
        if not flag.result_answer:
            msg_bot = messages[0]
        else:
            msg_bot = messages[2]
            flag.changing_result_a(False)
    else:
        msg_bot = messages[1]
    context.bot.send_photo(chat.id, img)
    logger.info('Картинка отправлена.')
    if chat.id != int(TELEGRAM_CHAT_ID):
        context.bot.send_message(chat.id, 'Чувак, не делай так больше!')
        logger.info('Сообщение отправлено!')
    else:
        context.bot.send_message(chat.id, msg_bot)
        logger.info('Сообщение отправлено!')
        logging.info('Сообщение отправлено!')
        flag.changing_result_w(True)
