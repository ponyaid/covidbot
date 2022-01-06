import telebot
import os
import time
import codecs
import common.tg_analytics as tga

from functools import wraps
from telebot import types
from jinja2 import Template
from dotenv import load_dotenv
from services.country_service import CountryService
from services.statistics_service import StatisticsService
from flask import Flask, request, abort


load_dotenv()  # take environment variables from .env.

# bot initialization
token = os.getenv('API_BOT_TOKEN')
bot = telebot.TeleBot(token)
user_steps = {}
known_users = []
stats_service = StatisticsService()
country_service = CountryService()

commands = {
    'start': 'Start using this bot',
    'country': 'Please, write a country name',
    'statistics': 'Statistics by users queries',
    'help': 'Useful information about this bot',
    'contacts': 'Developer contacts'
}


def get_user_step(uid):
    if uid in user_steps:
        return user_steps[uid]
    else:
        known_users.append(uid)
        user_steps[uid] = 0
        return user_steps[uid]


# decorator for bot actions
def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(message, *args, **kwargs):
            bot.send_chat_action(chat_id=message.chat.id, action=action)
            return func(message, *args, **kwargs)
        return command_func
    return decorator


# start command handler
@bot.message_handler(commands=['start'])
@send_action('typing')
# @save_user_activity()
def start_command_handler(message):
    cid = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(
        text='send location', request_location=True)
    markup.add(button_geo)
    bot.send_message(cid, 'Hello, {0}, please choose command from the menu'.format(message.chat.username),
                     reply_markup=markup)
    help_command_handler(message)


# country command handler
@bot.message_handler(commands=['country'])
@send_action('typing')
def country_command_handler(message):
    cid = message.chat.id
    user_steps[cid] = 1
    bot.send_message(
        cid, '{0}, write name of country please'.format(message.chat.username))


# geo command handler
@bot.message_handler(commands=['location'])
@send_action('typing')
def geo_command_handler(message):
    cid = message.chat.id
    geo_result = country_service.get_country_information(
        message.location.latitude, message.location.longitude)
    statistics = stats_service.get_statistics_by_country_name(
        geo_result['countryName'], message.chat.username)
    user_steps[cid] = 0
    bot.send_message(cid, statistics, parse_mode='HTML')


# country statistics command handler
@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1)
@send_action('typing')
def country_statistics_command_handler(message):
    cid = message.chat.id
    country_name = message.text.strip()

    try:
        statistics = stats_service.get_statistics_by_country_name(
            country_name, message.chat.username)
    except Exception as e:
        raise e

    user_steps[cid] = 0
    bot.send_message(cid, statistics, parse_mode='HTML')


# query statistics command handler
@bot.message_handler(commands=['statistics'])
@send_action('typing')
def statistics_command_handler(message):
    cid = message.chat.id
    bot.send_message(
        cid, stats_service.get_statistics_of_users_queries(), parse_mode='HTML')


# help command handler
@bot.message_handler(commands=['help'])
@send_action('typing')
def help_command_handler(message):
    cid = message.chat.id
    help_text = 'The following commands are available \n'
    for key in commands:
        help_text += '/' + key + ': '
        help_text += commands[key] + '\n'
    help_text += 'COVID_22_BOT speaks english, be careful and take care'
    bot.send_message(cid, help_text)


# contacts command handler
@bot.message_handler(commands=['contacts'])
@send_action('typing')
def contacts_command_handler(message):
    cid = message.chat.id
    with codecs.open('templates/contacts.html', 'r', encoding='UTF-8') as file:
        template = Template(file.read())
        bot.send_message(cid, template.render(
            user_name=message.chat.username), parse_mode='HTML')


# default text messages and hidden statistics command handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
@send_action('typing')
def default_command_handler(message):
    cid = message.chat.id
    if message.text[:int(os.getenv('PASS_CHAR_COUNT'))] == os.getenv('STAT_KEY'):
        st = message.text.split(' ')
        if 'txt' in st:
            tga.analysis(st, cid)
            with codecs.open('%s.txt' % cid, 'r', encoding='UTF-8') as file:
                bot.send_document(cid, file)
                tga.remove(cid)
        else:
            messages = tga.analysis(st, cid)
            bot.send_message(cid, messages)
    else:
        with codecs.open('templates/idunnocommand.html', 'r', encoding='UTF-8') as file:
            template = Template(file.read())
            bot.send_message(cid, template.render(
                text_command=message.text), parse_mode='HTML')


# set web hook
app = Flask(__name__)


@app.route('/')
def index():
    return '', 200


@app.route('/' + token, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)


# Remove webhook
bot.remove_webhook()
time.sleep(0.1)
# Set webhook
bot.set_webhook(url=os.getenv('SERVER_URL') + '/' + token,
                certificate=open(os.getenv('WEBHOOK_SSL_CERT'), 'r')
                )

# application entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=int(os.environ.get('PORT', 8443)),
            ssl_context=(os.getenv('WEBHOOK_SSL_CERT'),
                         os.getenv('WEBHOOK_SSL_PRIV')),
            debug=True
            )


# if __name__ == '__main__':
#     bot.polling(none_stop=True, interval=0)
