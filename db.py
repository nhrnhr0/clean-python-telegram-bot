# myclient = pymongo.MongoClient("mongodb://localhost:27017/")
# print(myclient.list_database_names())
# mydb = myclient["mydatabase3"]
# usersCollection = mydb["customers3"]
# usersCollection.insert_one({"name": "John", "address": "Highway 37"})
from decouple import config
import pymongo
import pytz
import datetime
from bson.codec_options import CodecOptions
# create a singleton class to manage the mongo database
MONGO_URL = config('MONGO_URL')
MONGO_DB = config('MONGO_DB')
class MongoDB:
    __instance = None
    def __init__(self):
        self.myclient = pymongo.MongoClient(MONGO_URL)
        self.mydb = self.myclient[MONGO_DB]
        self.usersCollection = self.mydb['users']
        self.messagesCollection = self.mydb['messages']
        self.notificationsCollection = self.mydb['notifications']
        #self.usersCollection.insert_one({"name": "John", "address": "Highway 37"})
    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance
    
    # def get_user(self, user_id):
    #     return self.usersCollection.find_one({"_id": user_id})
    
    # def create_user(self, user_id, user_preferences, telegram_info):
    #     self.usersCollection.insert_one({"_id": user_id, "preferences": user_preferences, "telegram_info": telegram_info})
    
    # def update_user(self, user_id, user_preferences, telegram_info):
    #     self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences": user_preferences, "telegram_info": telegram_info}})
        
    # def update_user_preferences(self, user_id, user_preferences):
    #     self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences": user_preferences}})
    
    # def update_user_telegram_info(self, user_id, telegram_info):
    #     self.usersCollection.update_one({"_id": user_id}, {"$set": {"telegram_info": telegram_info}})
    def get_or_create_user(self, user_id, user_preferences, telegram_info):
        user = self.usersCollection.find_one({"_id": user_id})
        if user is None:
            self.usersCollection.insert_one({"_id": user_id, "preferences": user_preferences, "telegram_info": telegram_info})
            return self.usersCollection.find_one({"_id": user_id})
        else:
            return user
    
    
    def save_user_message(self, user_id, message_id, message_dict):
        self.messagesCollection.insert_one({"_id": message_id, "user_id": user_id, "message": message_dict})
        
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"last_message": message_dict}})
    
    def save_last_notification(self, user_id):
        time = datetime.datetime.now(tz=pytz.timezone('Israel'))
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"last_notification_time": time}})
        self.notificationsCollection.insert_one({'user_id': user_id, 'time': time})
    def get_users_to_be_notified(self):
        # current time in Israel
        tz = pytz.timezone('Israel')
        current_time = datetime.datetime.now(tz)
        hh_mm_str = current_time.strftime("%H:%M")
        # find all users that the preferences.notification_time == hh_mm_str
        # make sure that passed at least preferences.send_notification_if_user_dont_send_info_for (06:00 = 6 hours) from the last notification sent to the user
        # make sure that passed at least preferences.send_notification_if_user_dont_send_info_for (06:00 = 6 hours) from the messsage the user sent
        users =  self.usersCollection.with_options(codec_options=CodecOptions(tz_aware=True,tzinfo=pytz.timezone('Israel'))).find({"preferences.notification_time": hh_mm_str,})# "preferences.send_notification_if_user_dont_send_info_for": {"$gte": self.get_last_notification_time(user_id)}})
        ret = []
        for user in users:
            # check last notification time
            preferd_notification_offset = int(user.get('preferences').get('send_notification_if_user_dont_send_info_for'))
            last_notification_time = user.get('last_notification_time')
            if not last_notification_time is None:
                #last_notification_time = datetime.datetime.strptime(last_notification_time, '%Y-%m-%d %H:%M:%S.%f')
                #last_notification_time = last_notification_time.replace(tzinfo=pytz.timezone('Israel'))
                secounds_pasted_from_last_notification = (current_time - last_notification_time).total_seconds()
                #prefered_secounds_pasted = user.get('preferences').get('send_notification_if_user_dont_send_info_for'):
                if  secounds_pasted_from_last_notification < preferd_notification_offset:
                    continue
            
            last_message = user.get('last_message')
            if not last_message is None:
                
                last_message_time = datetime.datetime.fromtimestamp(last_message.get('date'),tz=pytz.timezone('Israel')) # 1658747585
                secounds_pasted_from_last_message = (current_time - last_message_time).total_seconds()
                #prefered_secounds_passed = 
                if  secounds_pasted_from_last_message < preferd_notification_offset:
                    continue
            ret.append(user)
            # check last message time
        return ret