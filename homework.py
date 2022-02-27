from json import JSONDecodeError
import logging
import os
import sys
import time
import traceback
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

import botfilling

load_dotenv()


TELEGRAM_TOKEN = os.getenv('TOKEN_T')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
PRACTICUM_TOKEN = os.getenv('TOKEN_Y')

# НЕ ПРОХОДИТ ТЕСТЫ
# SLEEP_TIME = int(os.getenv('SLEEP_TIME','30'))

SLEEP_TIME = 30


ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# Глобальные логи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(levelname)s-%(message)s'
)


# Исключение при ошибке получения API
class ApiReceivingError(Exception):
    """Исключение при ошибке получения API."""

    pass

# Исключение при неверном значении таймера
class TimerHasDropped(ValueError):
    """Исключение при падении таймера."""

    pass


# Исключение запроса
class RequestsError(Exception):
    """Ошибка запроса."""

    pass


def is_timer_good(time):
    """Если условия не выполняются бот падает."""
    if time <= 0 or time >= 36000:
        msg = 'Неверное значение таймера!'
        botfilling.logger.error(msg)
        raise TimerHasDropped(msg)


def error_tg_handler(update, context):
    """Отправляем ошибку юзеру и разработчику."""
    if update.effective_message:
        msg_users = 'Пардон! Возникла ошибочка, но мы ее уже устраняем.'
        update.effective_message.reply_text(msg_users)
    info_box = []
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    if update.effective_user:
        bad_user = (
            str(update.effective_user.id)
            + update.effective_user.first_name
        )
        info_box.append(f' с пользователем {bad_user}')
    if update.effective_chat:
        info_box.append(f' внутри чата <i>{update.effective_chat.title}</i>')
        if update.effective_chat.username:
            info_box.append(f' (@{update.effective_chat.username})')
    msg_dev = (
        f"Ошибка <code>{context.error}</code> случилась {''.join(info_box)}."
        f"Полная трассировка:\n\n<code>{trace}</code>"
    )
    context.bot.send_message(TELEGRAM_CHAT_ID, msg_dev)
    botfilling.logger.error('Бот сломался!')
    logging.error('Бот работает не так.')


def send_message(bot, message: str):
    """Бот отправляет сообщение и стикер."""
    try:
        img = open(botfilling.PICTURES['ben_result'], 'rb')
        bot.send_photo(TELEGRAM_CHAT_ID, img)
        botfilling.logger.info('Картинка отправлена.')
    except TelegramError:
        botfilling.logger.error('Картинка не отправлена!')

    msg = """Как и многие жизненные проблемы,
    эту можно решить сгибанием.
    Держи ответ!: """

    bot.send_message(TELEGRAM_CHAT_ID, msg)
    botfilling.logger.info('Сообщение отправлено!')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    botfilling.logger.info('Сообщение отправлено!')

    # Стикеры подогнаны под запрет не более двух аргументов на вход
    stickers = {
        "Ура!": botfilling.STICKERS['Выполнено'],
        "взята": botfilling.STICKERS['Доработай'],
        "замечания": botfilling.STICKERS['Не проверено']
    }
    try:
        for key, value in stickers.items():
            if key in message:
                bot.send_sticker(TELEGRAM_CHAT_ID, value)
    except FileNotFoundError:
        botfilling.logger.error('Стикеры не найдены!')
        raise FileNotFoundError


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
    except RequestsError:
        msg = 'Ошибка запроса! Проверьте, что передано в запрос!'
        botfilling.logger.error(msg)
        raise RequestsError(msg)
    if response.status_code != HTTPStatus.OK:
        msg = 'Ошибка в доступе к Практикуму.'
        botfilling.logger.error(msg)
        raise ApiReceivingError(msg)
    try:
        return response.json()
    except JSONDecodeError:
        msg = 'Отсутствует JSON.'
        botfilling.logger.error(msg)
        raise JSONDecodeError(msg)


def check_response(response):
    """Проверяем есть ли что в словаре(списке)."""
    if not isinstance(response, dict):
        raise TypeError('Некорректный тип responce.')
    if 'homeworks' not in response:
        msg = 'Нет ключа: homeworks'
        botfilling.logger.error(msg)
        raise KeyError(msg)
    test_list = response.get('homeworks')
    if not test_list:
        return None
    return test_list[0]


def parse_status(homework: dict) -> str:
    """Формируем сообщение, если доступны все данные."""
    if not homework:
        return None
    if not isinstance(homework, dict):
        msg = 'homework не словарь'
        botfilling.logger.error(msg)
        raise KeyError(msg)
    if 'status' not in homework:
        msg = 'status нет в homework'
        botfilling.logger.error(msg)
        raise KeyError(msg)
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        msg = f'{homework_status} нет в HOMEWORK_STATUSES.'
        botfilling.logger.error(msg)
        raise ValueError(msg)
    verdict = HOMEWORK_STATUSES[homework_status]
    if not 'homework_name' in homework:
        msg = 'Нет ключа homework_name'
        botfilling.logger.error(msg)
        raise KeyError(msg)
    homework_name = homework.get('homework_name')
    msg = (
        f'Изменился статус проверки работы "{homework_name}"'
        f'.{verdict}'
    )
    return msg


def check_tokens() -> bool:
    """Если все токены в наличии и время в норме, то Трушечка."""
    tokens = {
        "ID разработчика": TELEGRAM_CHAT_ID,
        "ID бота": TELEGRAM_TOKEN,
        "ID Практикума": PRACTICUM_TOKEN,
    }
    result = True
    bad_tokens = [key for key, token in tokens.items() if not token]    
    if bad_tokens:
        msg = f'Отсутствуют {bad_tokens}'
        botfilling.logger.error(msg)
        result = False
    return result
# /ПОИСК


# Участок кода для обхода ошибки: 'main too complex(11)'
def obhod_tester(time, bot, flag):
    """Нужен только для обхода тестера."""
    is_timer_good(SLEEP_TIME )
    message = get_api_answer(time)
    answer = check_response(message)
    result = parse_status(answer)
    if result:
        send_message(bot, result)
        botfilling.logger.info('Сообщение отправлено.')
        flag.changing_result_a(True)
    current_timestamp = message.get(
        'current_date'
    )
    return current_timestamp


def main():
    """Основная логика работы бота."""
    flag = botfilling.MainFlags()
    if not check_tokens():
        AssertionError('Токены тю-тю...')
        sys.exit(1)
    bot = Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    updater.dispatcher.add_handler(
        CommandHandler('start', botfilling.wake_up)
    )
    updater.dispatcher.add_handler(
        CommandHandler('search', botfilling.start_search)
    )
    updater.dispatcher.add_handler(
        CommandHandler('stop', botfilling.stop_search)
    )
    updater.dispatcher.add_handler(
        MessageHandler(Filters.text, botfilling.say_answer)
    )
    updater.dispatcher.add_handler(
        MessageHandler(
            Filters.chat(chat_id=TELEGRAM_CHAT_ID),
            get_api_answer
        )
    )

    updater.dispatcher.add_error_handler(error_tg_handler)
    updater.start_polling()
    try:
        while True:
            if not flag.result_while:
                try:
                    current_timestamp = obhod_tester(
                        current_timestamp,
                        bot,
                        flag
                    )
                except TimeoutError:
                    pass
                except Exception as error:
                    message = f'Дангер! Паник!: {error}'
                    botfilling.logger.error(message)
                    botfilling.send_error_message(bot, message)
                time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        updater.idle()
    except Exception as error:
        botfilling.logger.critical(error)
        updater.idle()


if __name__ == '__main__':
    main()
