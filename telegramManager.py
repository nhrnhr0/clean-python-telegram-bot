from multiprocessing.dummy import Array
from turtle import up
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from consts import GREET_MESSAGE, NOTIFICATION_MESSAGE, SET_NOTIFICATION_MESSAGE, SET_NOTIFICATION_MESSAGE_ERROR,SUCCESS_NOTIFICATION_MESSAGE,SET_ALERT_DAYS_MESSAGE,NEXT_NOTIFICATION_TIME_MESSAGE
from db import MongoDB
from schedule import notification_thread_caller
import threading
import time
from decouple import config
import pytz
import re

import datetime
import asyncio
from telegram.ext import  CallbackQueryHandler

ADMIN_LOGS_CHAT_ID = config("ADMIN_LOGS_CHAT_ID")
TELEGRAM_TOEKN = config("TELEGRAM_TOKEN")
# create a singleton instance of the bot's application:
    # application = Application.builder().token(TELEGRAM_TOEKN.strip()).build()
    # time.sleep(3)
    # bot = application.bot
    # # on different commands - answer in Telegram
    # application.add_handler(CommandHandler("start", start))
    # application.add_handler(CommandHandler("help", help_command))
    # # on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
    # application.add_handler(MessageHandler(filters.ALL, bot_reviced_message))

    
    # # start the thread that will check if the user need to be notified
    # notification_thread_t = threading.Thread(target=notification_thread_caller, args=(bot,logger)).start()
    
    # # Run the bot until the user presses Ctrl-C
    # application.run_polling()
    # notification_thread_t.join()
class TelegramManager:
    __instance = None
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOEKN.strip()).build()
        time.sleep(3)
        self.bot = self.application.bot
        # set bot commands (start, help, set_alert_days, set_alert_time)
        my_commands = [
            ['start', 'תפריט ראשי ⚙️'],
            ['set_alert_days', 'הגדרת ימי ההתראה 🗓'],
            ['set_alert_time', 'הגדרת שעת ההתראה 🕑'],
        ]
        loop = asyncio.get_event_loop()
        set_commands = loop.run_until_complete(self.bot.set_my_commands(my_commands))
        print('======> done setting commands')
        #loop.close()

        
        # on different commands - answer in Telegram
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("set_alert_days", set_alert_days))
        self.application.add_handler(CommandHandler("set_alert_time", set_alert_time_clicked))
        # if the message is replay to the set_alert_time_clicked and the message is a time in the correct format (HH:MM) - set the time to the user
        self.application.add_handler(MessageHandler(filters.Regex("^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]?$"), set_alert_time_clicked))
        self.application.add_handler(CallbackQueryHandler(set_alert_day_clicked, pattern="(^set_alert_day_clicked_.*$|^set_alert_days$)"))
        self.application.add_handler(CallbackQueryHandler(set_alert_time_clicked, pattern="(^set_alert_time_clicked_.*$|^set_alert_time$)"))
        #self.application.add_handler(CallbackQueryHandler)
        # on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
        self.application.add_handler(MessageHandler(filters.ALL, bot_reviced_message))

        # start the thread that will check if the user need to be notified
        self.notification_thread_t = threading.Thread(target=notification_thread_caller, args=(self.bot,))
        self.notification_thread_t.daemon = True
        self.notification_thread_t.start()
        
        
    def start(self):
        # Run the bot until the user presses Ctrl-C
        self.application.run_polling()
        #self.notification_thread_t.join()
    def stop(self):
        self.application.stop()
        self.notification_thread_t.join()
    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance



async def set_alert_time_clicked(update: Update, context) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    current_alert_time = MongoDB.getInstance().get_user_time_preferences(user.id)
    #keyboard = create_time_keyboard_markup_for_user(user_preferences)
    #reply_markup = InlineKeyboardMarkup(keyboard)
    # current_alert_time in israel time:
    #user_preferences_time = 
    
    if update.message or update.edited_message:
        msg = update.message if update.message else update.edited_message
        requested_alert_time = msg.text
        has_error = False
        # check if requested_alert_time is in the right format of HH:MM when HH is between 00 and 23 and MM is between 00 and 59
        
        try:
            my_re = '^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]?$'
            if re.match(my_re, requested_alert_time):
                # convert the time to
                hh, mm = requested_alert_time.split(":")
                hh = int(hh)
                mm = int(mm)
                if hh >= 0 and hh <= 23 and mm >= 0 and mm <= 59:
                    # check if the requested_alert_time is not the same as the current_alert_time
                    #if current_alert_time != requested_alert_time:
                        # update the user's time preference
                    MongoDB.getInstance().update_user_time_preferences(user.id, requested_alert_time)
                        # send a message to the user that the time was updated
                    #dbUser = MongoDB.getInstance().get_user(user.id)
                    #MongoDB.getInstance().update_user_next_notification_time(user.id, MongoDB.getInstance().recalculate_next_notification_time(dbUser))
                    await user_updated_notification_preference(user)
                    next_notification = MongoDB.getInstance().get_user_next_notification_time(user.id)
                    next_notification_in_secounds = (next_notification-datetime.datetime(1970,1,1, tzinfo=pytz.timezone('Israel'))).total_seconds()
                    now_in_secounds = (datetime.datetime.now(tz=pytz.utc) - datetime.datetime(1970,1,1, tzinfo=pytz.timezone('UTC'))).total_seconds()
                    
                    time_left = next_notification_in_secounds - now_in_secounds#datetime.datetime.now(tz=pytz.utc) - next_notification
                    time_left_str = datetime.timedelta(seconds=time_left)
                    time_left_str = td_format(time_left_str)
                    #time_left_str = time_left_str.split('.')[0]
                    await msg.reply_text(SUCCESS_NOTIFICATION_MESSAGE.format(requested_alert_time,time_left_str), parse_mode='HTML')
                else:
                    has_error = True
            else:
                has_error = True
        except:
            has_error = True
        if has_error:
            if requested_alert_time == '/set_alert_time':
                next_notification = MongoDB.getInstance().get_user_next_notification_time(user.id)
                next_notification_in_secounds = (next_notification-datetime.datetime(1970,1,1, tzinfo=pytz.timezone('Israel'))).total_seconds()
                now_in_secounds = (datetime.datetime.now(tz=pytz.utc) - datetime.datetime(1970,1,1, tzinfo=pytz.timezone('UTC'))).total_seconds()
                
                time_left = next_notification_in_secounds - now_in_secounds#datetime.datetime.now(tz=pytz.utc) - next_notification
                time_left_str = datetime.timedelta(seconds=time_left)
                time_left_str = td_format(time_left_str)
                message_html =  SET_NOTIFICATION_MESSAGE.format(current_alert_time, time_left_str)
                await update.effective_user.send_message(message_html,parse_mode='HTML')
            else:
                await msg.reply_text(SET_NOTIFICATION_MESSAGE_ERROR)
    else:
        next_notification = MongoDB.getInstance().get_user_next_notification_time(user.id)
        next_notification_in_secounds = (next_notification-datetime.datetime(1970,1,1, tzinfo=pytz.timezone('Israel'))).total_seconds()
        now_in_secounds = (datetime.datetime.now(tz=pytz.utc) - datetime.datetime(1970,1,1, tzinfo=pytz.timezone('UTC'))).total_seconds()
        
        time_left = next_notification_in_secounds - now_in_secounds#datetime.datetime.now(tz=pytz.utc) - next_notification
        time_left_str = datetime.timedelta(seconds=time_left)
        time_left_str = td_format(time_left_str)
        message_html =  SET_NOTIFICATION_MESSAGE.format(current_alert_time,time_left_str)
        #await query.(message_html, reply_markup=ForceReply())
        await update.effective_user.send_message(message_html,parse_mode='HTML')
    return None

def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('ימים',         60*60*24),
        ('שעות',        60*60),
        ('דקות',      60),
        ('שניות',      1)
    ]

    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            #has_s = 's' if period_value > 1 else ''
            if period_value > 0:
                strings.append("%s %s" % (period_value, period_name))
    return ", ".join(strings)

async def set_alert_day_clicked(update: Update, context) -> None:
    query = update.callback_query
    user = update.effective_user
    day_idx = query.data.split("_")[-1]
    if day_idx == "cancel":
        # return to the maib menu
        
        #await query.edit_message_reply_markup(main_menu_keyboard(query.from_user.id))
        await query.edit_message_text(GREET_MESSAGE.format(user.mention_html()),parse_mode='HTML', reply_markup=main_menu_keyboard(query.from_user.id))
        return
    
    user_preferences = MongoDB.getInstance().get_user_week_days_preferences(user.id)
    if day_idx != 'days':
        user_preferences[int(day_idx)] = not user_preferences[int(day_idx)]
        MongoDB.getInstance().update_user_week_days_preferences(user.id, user_preferences)
        await user_updated_notification_preference(user)
    keyboard = create_days_keyboard_markup_for_user(user_preferences)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(SET_ALERT_DAYS_MESSAGE, parse_mode='HTML', reply_markup=reply_markup)
    #await query.edit_message_reply_markup(reply_markup=reply_markup)
    await query.answer()
    return None
async def user_updated_notification_preference(user):
    
    # calculate the users next notification time
    user_preferences_time = MongoDB.getInstance().get_user_time_preferences(user.id)
    user_preferences_days = MongoDB.getInstance().get_user_week_days_preferences(user.id)
    # get the current time
    current_time = datetime.datetime.now(tz=pytz.timezone('Israel'))
    # set the time to the user_preferences_time
    next_alert =  current_time.replace(hour=int(user_preferences_time.split(':')[0]), minute=int(user_preferences_time.split(':')[1]))
    # if the next_alert time of already passed today / the day is not in the user_preferences_days, set the next_alert to the next day
    while next_alert < current_time or not user_preferences_days[(next_alert.weekday()+1)%7]:
        next_alert = next_alert + datetime.timedelta(days=1)
    # update the user's next notification time
    MongoDB.getInstance().update_user_next_notification_time(user.id, next_alert)

    
def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("עדכן שעת התראה 🕑", callback_data="set_alert_time")],
        [InlineKeyboardButton("עדכן ימי התראה 🗓", callback_data="set_alert_days")],
        #[InlineKeyboardButton("עזרה", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup
def create_days_keyboard_markup_for_user(user_preferences):
    def get_days_of_week_options(user_preferences: list):
        days_of_week = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
        options1 = []
        options2 = []
        options3 = []
        options4 = []
        v_or_cros = lambda x: "✅" if x else "❌"
        is_day_active = lambda i, user_pref: v_or_cros(user_pref[i])
        for i in range(3):
            options1.append(InlineKeyboardButton(days_of_week[i] + is_day_active(i,user_preferences), callback_data='set_alert_day_clicked_' + str(i)))
        for i in range(3, 6):
            options2.append(InlineKeyboardButton(days_of_week[i] + is_day_active(i,user_preferences), callback_data='set_alert_day_clicked_' + str(i)))
        for i in range(6, 7):
            options2.append(InlineKeyboardButton(days_of_week[i] + is_day_active(i,user_preferences), callback_data='set_alert_day_clicked_' + str(i)))
        
        #options4.append(InlineKeyboardButton("בחר שעה🕑", callback_data='set_alert_time_clicked'))
        options4.append(InlineKeyboardButton("חזור🔙", callback_data="set_alert_day_clicked_cancel"))
        keybaotd_layout = [options1,options2, options4]
        return [keybaotd_layout[0], keybaotd_layout[1], keybaotd_layout[2]]
    return get_days_of_week_options(user_preferences)
async def set_alert_days(update: Update, context) -> None:
    # return 7 days of the week as togling options
    # 3 in a row
    # get user preferences days from db:
    user = update.effective_user
    user_preferences = MongoDB.getInstance().get_user_week_days_preferences(user.id)
    keyboard = create_days_keyboard_markup_for_user(user_preferences)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(SET_ALERT_DAYS_MESSAGE, reply_markup=reply_markup)
    
async def start(update: Update, context) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    _main_menu_keyboard = main_menu_keyboard(user.id)
    #next_notification_time = MongoDB.getInstance().get_user_next_notification_time(user.id)
    await update.message.reply_html(GREET_MESSAGE.format(user.mention_html(), ), reply_markup=_main_menu_keyboard)
    # with date and time
    # next_notification_time_str = next_notification_time.strftime("%d-%m-%Y %H:%M")
    # time_left = next_notification_time - datetime.datetime.now(tz=pytz.timezone('Israel'))
    # time_left_hours = 
    # await update.message.reply_html(NEXT_NOTIFICATION_TIME_MESSAGE.format(next_notification_time_str,time_left_str))
    get_or_create_user(user, user_preferences=None)
# async def help_command(update: Update, context) -> None:
#     """Send a message when the command /help is issued."""
#     await update.message.reply_text("Help!")

# on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
async def bot_reviced_message(update: Update, context) -> None:
    #create_user_id_file(update.effective_user)
    dbUser = get_or_create_user(update.effective_user)
    # step 1: forwared the message to ADMIN_LOGS_CHAT_ID:  
    bot = context.bot
    res = await bot.forward_message(chat_id=ADMIN_LOGS_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
    
    user = update.effective_user
    MongoDB.getInstance().save_user_message(user.id, update.effective_message.message_id, update.effective_message.to_dict())
    await update.message.reply_text("👍 קיבלתי",reply_to_message_id=update.effective_message.message_id)
    
    pass

def get_or_create_user(telegramUser, user_preferences=None):
    user_preferences = user_preferences or {
            'notification_time': "14:00",
            'send_notification_if_user_dont_send_info_for':360,
        }
    user_id = telegramUser.id
    dbUser = MongoDB.getInstance().get_or_create_user(user_id, user_preferences, telegram_info=telegramUser.to_dict())
    return dbUser

async def send_nofication(bot, dbUser):
    user_id = dbUser['_id']
    message = NOTIFICATION_MESSAGE
    # save the current timestemp to last_notification/<user_id>.json
    MongoDB.getInstance().save_last_notification(user_id)
    await bot.send_message(chat_id=user_id, text=message)
    #logger.info(f"Notification sent to {chat_id}")
    #name = dbUser.get('telegram_info').get('username')
    try:
        await bot.send_message(chat_id=ADMIN_LOGS_CHAT_ID, text=f"Notification sent to {user_id}")
    except:
        pass