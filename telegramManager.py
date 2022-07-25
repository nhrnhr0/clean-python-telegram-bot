from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from consts import GREET_MESSAGE, NOTIFICATION_MESSAGE
from db import MongoDB
from schedule import notification_thread_caller
import threading
import time
from decouple import config
import datetime

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
        # on different commands - answer in Telegram
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_command))
        # on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
        self.application.add_handler(MessageHandler(filters.ALL, bot_reviced_message))

        # start the thread that will check if the user need to be notified
        self.notification_thread_t = threading.Thread(target=notification_thread_caller, args=(self.bot,)).start()
        
        
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

async def start(update: Update, context) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(GREET_MESSAGE.format(user.mention_html()),)
    # save user full data to file in users/<user_id>
    get_or_create_user(user, user_preferences=None)
async def help_command(update: Update, context) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

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
    name = dbUser.get('telegram_info').get('username')
    await bot.send_message(chat_id=ADMIN_LOGS_CHAT_ID, text=f"Notification sent to {name}")