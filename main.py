
import logging
import os

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import datetime
from consts import GREET_MESSAGE, NOTIFICATION_MESSAGE

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
import json

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(GREET_MESSAGE.format(user.mention_html()),)
    # save user full data to file in users/<user_id>
    create_user_id_file(user)
        
async def help_command(update: Update, context) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

ADMIN_LOGS_CHAT_ID = os.environ.get("ADMIN_LOGS_CHAT_ID")
# on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
async def bot_reviced_message(update: Update, context) -> None:
    create_user_id_file(update.effective_user)
    # step 1: forwared the message to ADMIN_LOGS_CHAT_ID:  
    bot = context.bot
    res = await bot.forward_message(chat_id=ADMIN_LOGS_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
    print(res)
    # step 2: save the message to a file in the users/<user_id> folder
    # step 2.5: create a folder users/<user_id> if it doesn't exist
    user = update.effective_user
    if not os.path.exists(f"messages/{user.id}"):
        os.makedirs(f"messages/{user.id}")
    # write the message timestamp to the users/<user_id>/last_message.txt
    with open(f"last_messages/{user.id}.json", "w") as f:
        #f.write(f"{update.effective_message.to_dict()}")
        json.dump(update.effective_message.to_dict(), f, indent=4)
    # step 3: save the message to a file in the users/<user_id> folder with the timestamp as the file name (file can be message text or sticker or photo or anything else)
    with open(f"messages/{user.id}/{update.effective_message.date.strftime('%Y-%m-%d_%H-%M-%S')}.json", "w") as f:
            json.dump(update.effective_message.to_dict(), f)

    # step 4: send a thumbs up emoji to the user Quete the user's message
    await update.message.reply_text("👍 קיבלתי",reply_to_message_id=update.effective_message.message_id)
    
    

def create_user_id_file(user, user_preferences = None):
    user_preferences = user_preferences or {
            'notification_time': "14:00",
            'send_notification_if_user_dont_send_info_for': "06:00",# 6 hours
        }
    # if the user file doesn't exist, create it, and write the user's preferences to it
    if not os.path.exists(f"users/{user.id}.json"):
        with open(f"users/{user.id}.json", "w") as f:
            telegram_info = user.to_dict()
            
            info = {**telegram_info, **user_preferences}
            
            json.dump(info, f, indent=4)
            logger.info(f"User {user.id} saved to file")
    else:
        logger.info(f"User {user.id} already exists in file")
    
async def send_nofication(bot, chat_id):
    message = NOTIFICATION_MESSAGE
    # save the current timestemp to last_notification/<user_id>.json
    with open(f"last_notifications/{chat_id}.json", "w") as f:
        f.write(str(datetime.datetime.now()))
    await bot.send_message(chat_id=chat_id, text=message)
    logger.info(f"Notification sent to {chat_id}")
    await bot.send_message(chat_id=ADMIN_LOGS_CHAT_ID, text=f"Notification sent to {chat_id}")
# the thread will be started and will check every 30 seconds if any user need to be notified    
import threading
import time
import asyncio
# we send notifications to the user every 30 seconds
# if it's the notification_time the user is asked for
# and the user did not send any message for send_notification_if_user_dont_send_info_for
def notification_thread_caller(bot):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(notification_thread(bot))
    loop.close()
async def notification_thread(bot):
    while True:
            time.sleep(5)
            try:
                for user_filename in os.listdir("users"):
                    with open(f"users/{user_filename}", "r") as f:
                        user_info = json.load(f)
                        should_send_nofication = True
                        # check if the user need to be notified
                        notification_time = user_info.get('notification_time', None)
                        if notification_time != time.strftime("%H:%M"):
                            should_send_nofication=False
                        else:
                            last_message = None
                            try:
                                with open(f"last_messages/{user_info['id']}.json", "r") as f:
                                    last_message = f.read()
                            except FileNotFoundError:
                                pass
                            if last_message is not None:
                                last_message_json = json.loads(last_message)
                                time_from_last_message_secounds = time.time() - last_message_json['date']
                                user_prefered_offset_secounds = int(user_info['send_notification_if_user_dont_send_info_for'].split(':')[0]) * 60 + int(user_info['send_notification_if_user_dont_send_info_for'].split(':')[1]) * 60
                                if time_from_last_message_secounds < user_prefered_offset_secounds:
                                    should_send_nofication = False

                            last_notification = None
                            try:
                                with open(f"last_notifications/{user_info['id']}.json", "r") as f:
                                    last_notification = f.read()
                            except FileNotFoundError:
                                pass
                            if last_notification is not None:
                                # convenrt last_notification to datetime
                                last_notification_timestemp = datetime.datetime.strptime(last_notification, "%Y-%m-%d %H:%M:%S.%f")
                                time_from_last_notification = datetime.datetime.now() - last_notification_timestemp
                                user_prefered_offset_secounds = datetime.timedelta(minutes=int(user_info['send_notification_if_user_dont_send_info_for'].split(':')[0]) * 60 + int(user_info['send_notification_if_user_dont_send_info_for'].split(':')[1]))
                                if time_from_last_notification < user_prefered_offset_secounds:
                                    should_send_nofication = False
                            
                            
                        if should_send_nofication:
                            await send_nofication(bot, user_info['id'])
                        logger.info(f"Notification checked for {user_info['id']}, should_send_nofication: {should_send_nofication}")
            except Exception as e:
                logger.error(f"Error in notification thread: {e}")
                continue
    
TELEGRAM_TOEKN = os.environ.get("TELEGRAM_TOKEN")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOEKN).build()
    bot = application.bot
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    # on any other message (incoming messages, images, videos, audio, etc) - replay to the admin chat, send a tumbs up emoji to the user, and store the last message from the user with the user id, message, and timestamp
    application.add_handler(MessageHandler(filters.ALL, bot_reviced_message))

    
    # start the thread that will check if the user need to be notified
    notification_thread_t = threading.Thread(target=notification_thread_caller, args=(bot,)).start()
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling()
    notification_thread_t.join()

if __name__ == "__main__":
    main()