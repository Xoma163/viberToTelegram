import os
import threading
from tempfile import NamedTemporaryFile

import requests
import telebot
from dotenv import load_dotenv
from flask import Flask, request, Response
from viberbot import BotConfiguration, Api
from viberbot.api.messages import TextMessage, PictureMessage, FileMessage
from viberbot.api.viber_requests import ViberMessageRequest

load_dotenv()

tg_bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

viber_bot = Api(BotConfiguration(
    name=os.getenv('USER2_VIBER_NAME'),
    avatar=os.getenv('USER2_VIBER_AVATAR_URL'),
    auth_token=os.getenv("VIBER_TOKEN")
))
app = Flask(__name__)

if __name__ == "__main__":
    threading.Thread(target=app.run,
                     kwargs={'host': '0.0.0.0', 'port': 20001, 'debug': False, 'use_reloader': False}).start()
    threading.Thread(target=tg_bot.polling,
                     kwargs={'none_stop': True, 'interval': 0, 'timeout': 86400}).start()


@tg_bot.message_handler(content_types=['text', 'photo', 'document'])
def telegram(message):
    """
    https://developers.viber.com/docs/api/python-bot-api/
    """
    if not str(message.from_user.id) == os.getenv('USER2_TELEGRAM_ID'):
        return
    if message.document:
        file_id = message.document.file_id
        file = tg_bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{os.getenv('TELEGRAM_TOKEN')}/{file.file_path}"
        text = message.caption
        viber_message = TextMessage(text=text)
        viber_bot.send_messages(os.getenv('USER1_VIBER_ID'), viber_message)
        viber_message = FileMessage(media=file_url, size=message.document.file_size,
                                    file_name=message.document.file_name)
    elif message.photo:
        file_id = message.photo[-1].file_id
        file = tg_bot.get_file(file_id)
        photo_url = f"https://api.telegram.org/file/bot{os.getenv('TELEGRAM_TOKEN')}/{file.file_path}"
        text = message.caption
        viber_message = PictureMessage(media=photo_url, text=text)
    else:
        text = message.text
        viber_message = TextMessage(text=text)
    viber_bot.send_messages(os.getenv('USER1_VIBER_ID'), viber_message)


@app.route('/', methods=['POST'])
def viber():
    if not viber_bot.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return Response(status=403)

    viber_request = viber_bot.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        if not viber_request.sender.id == os.getenv('USER1_VIBER_ID'):
            return Response(status=200)
        message = viber_request.message

        if isinstance(message, TextMessage):
            text = message.text
            tg_bot.send_message(os.getenv("USER2_TELEGRAM_ID"), text)
        elif isinstance(message, PictureMessage):
            text = message.text
            photo_url = message.media
            tg_bot.send_photo(os.getenv("USER2_TELEGRAM_ID"), photo_url, text)
        elif isinstance(message, FileMessage):
            document_url = message.media
            content = requests.get(document_url).content
            tmp = NamedTemporaryFile()
            tmp.write(content)
            tmp.name = message.file_name
            tmp.seek(0)
            tg_bot.send_document(os.getenv("USER2_TELEGRAM_ID"), tmp)

    return Response(status=200)
