
import os
from decouple import config
from db import MongoDB
import time

import datetime

from schedule import notification_thread_caller
from telegramManager import TelegramManager


import json

def main() -> None:
    print('starting the bot')
    TelegramManager.getInstance().start()
    print('bot is started')
    # Create the Application and pass it your bot's token.
    

if __name__ == "__main__":
    main()