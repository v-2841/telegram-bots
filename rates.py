import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiohttp import ClientSession
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters


load_dotenv()
Path('logs/').mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(name)s, %(levelname)s, %(funcName)s, %(message)s',
    handlers=[RotatingFileHandler(
        'logs/main.log', maxBytes=100000, backupCount=10)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
pairs = [
    ['eur', 'usd'],
    ['usd', 'rub'],
    ['eur', 'rub'],
    ['amd', 'rub'],
    ['rub', 'amd'],
    ['usd', 'amd'],
    ['eur', 'amd'],
]
translation = {
    'usd': 'Доллар',
    'eur': 'Евро',
    'rub': 'Рубль',
    'amd': 'Драм',
}
url_template = ('https://cdn.jsdelivr.net/gh/fawazahmed0/'
                + 'currency-api@1/latest/currencies/{}/{}.json')


async def get_rate(client, pair):
    async with client.get(url=url_template.format(*pair)) as response:
        data = await response.json()
        return (f'{translation[pair[0]]} -> {translation[pair[1]]}: '
                + f'{data[pair[1]]}')


async def get_date(client):
    url = url_template.format(*pairs[0])
    async with client.get(url) as response:
        data = await response.json()
        return f'Дата: {data["date"]}'


async def rates(update, context):
    chat = update.effective_chat
    tasks = [asyncio.create_task(get_date(context.bot_data['client']))]
    for pair in pairs:
        tasks.append(asyncio.create_task(
            get_rate(context.bot_data['client'], pair)))
    rates = await asyncio.gather(*tasks)
    rates_text = '\n'.join(rates)
    await context.bot.send_message(
        chat_id=chat.id,
        text=(rates_text),
    )
    logger.info(f'Пользователь {chat.id} запросил курс')


async def wake_up(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup([
                ['Курс на сегодня']
            ], resize_keyboard=True)
    await context.bot.send_message(
        chat_id=chat.id,
        text=('Привет!'),
        reply_markup=buttons,
    )
    logger.info(f'Пользователь {chat.id} включил бота')


async def post_init(application: Application) -> None:
    application.bot_data['client'] = ClientSession()
    logger.info('Клиент ClientSession запущен')


async def post_shutdown(application: Application) -> None:
    await application.bot_data['client'].close()
    logger.info('Клиент ClientSession остановлен')


if __name__ == '__main__':
    application = Application.builder().token(
        os.getenv('TELEGRAM_TOKEN', 'token')).post_init(
            post_init).post_shutdown(post_shutdown).build()
    application.add_handler(CommandHandler('start', wake_up))
    application.add_handler(MessageHandler(
        filters.Regex('^Курс на сегодня$'), rates))
    application.run_polling()
