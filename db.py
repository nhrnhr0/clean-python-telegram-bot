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
    
    # def get_user_commands(self, user_id):
    #     user = self.usersCollection.find_one({"_id": user_id})
    #     if user is None:
    #         return None
    #     else:
    #         pref = user.get('preferences')
    #         set_alert_time = self.get_user_time_preferences(user_id)
    #         my_commands = [
    #             ['start', 'תפריט ראשי ⚙️'],
    #             ['set_alert_days', 'הגדרת ימי ההתראה 🗓'],
    #             ['set_alert_time', 'הגדרת שעת ההתראה 🕑 (' + set_alert_time + ')'],
    #         ]
    #         return my_commands
    def update_user_time_preferences(self, user_id, time_preferences):
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences.notification_pref_time": time_preferences}})
        
    def get_user_time_preferences(self, user_id):
        user = self.usersCollection.find_one({"_id": user_id})
        # defult = 09:00
        defult = datetime.time(9, 0, 0, 0, pytz.timezone('Israel'))
        if user is None:
            return None
        else:
            ret = user.get('preferences')#')#user['preferences']['alert']['week_days']
            if not ret is None:
                ret = ret.get('notification_pref_time')
                if not ret is None:
                    return ret
            # if the user has no preferences, set the user in db to default one (09:00)
            if ret is None:
                ret = defult
                ret = ret.strftime("%H:%M")
                self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences.notification_pref_time": ret}})
            return ret
    def recalculate_next_notification_time(self, dbUser):
        # get the user's time preferences
        time_preferences = self.get_user_time_preferences(dbUser['_id'])
        # get the user's week days preferences
        week_days_preferences = dbUser['preferences']['alert']['week_days']
        # get the current time
        current_time = datetime.datetime.now(pytz.timezone('Israel'))
        next_alert =  current_time.replace(hour=int(time_preferences[:2]), minute=int(time_preferences[3:]))
        # if the next_alert time of already passed today / the day is not in the user_preferences_days, set the next_alert to the next day
        while next_alert < current_time or not week_days_preferences[(next_alert.weekday()+1)%7]:
            next_alert = next_alert + datetime.timedelta(days=1)
        return next_alert
    def get_users_to_be_reminded(self):
        # get the current time
        current_time = datetime.datetime.now(pytz.timezone('Israel'))
        # get all the users that reminder_time > current_time and did not send us messages in the last 1 hour
        users = self.usersCollection.find({"reminder_time":{'$lte': current_time}, "last_message.date":{'$lte': current_time - datetime.timedelta(hours=1)}})
        return users
        
    def set_reminder_time(self, user_id, reminder_time):
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"reminder_time": reminder_time}})
    def update_user_next_notification_time(self, user_id, next_notification_time):
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"next_notification_time": next_notification_time}})
    def get_user_next_notification_time(self, user_id,):
        user = self.usersCollection.find_one({"_id": user_id})
        if user is None:
            return None
        else:
            ret = user.get('next_notification_time')
            if not ret is None:
                # convert the time to the user's timezone (Israel)
                ret = ret.replace(tzinfo=pytz.timezone('Israel'))
                return ret
            self.update_user_next_notification_time(user_id, self.recalculate_next_notification_time(user))
            
            ret = self.get_user_next_notification_time(user_id)
            return ret
    def get_user(self, user_id):
        user = self.usersCollection.find_one({"_id": user_id})
        return user
    def get_or_create_user(self, user_id, user_preferences, telegram_info):
        user = self.usersCollection.find_one({"_id": user_id})
        if user is None:
            self.usersCollection.insert_one({"_id": user_id, "preferences": user_preferences, "telegram_info": telegram_info})
            return self.usersCollection.find_one({"_id": user_id})
        else:
            return user
    def update_user_week_days_preferences(self, user_id, week_days_preferences):
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences.alert.week_days": week_days_preferences}})
    def get_user_week_days_preferences(self, user_id):
        user = self.usersCollection.find_one({"_id": user_id})
        if user is None:
            return None
        else:
            ret = user.get('preferences')#')#user['preferences']['alert']['week_days']
            if not ret is None:
                ret = ret.get('alert')
                if not ret is None:
                    ret = ret=ret.get('week_days')
                    if not ret is None:
                        return ret
            # if the user has no preferences, set the user in db to default ones [True, True, True, True, True, True, False]
            if ret is None:
                ret = [True, True, True, True, True, True, False]
                self.usersCollection.update_one({"_id": user_id}, {"$set": {"preferences.alert.week_days": ret}})
            return ret
    def save_user_message(self, user_id, message_id, message_dict):
        self.messagesCollection.insert_one({"_id": message_id, "user_id": user_id, "message": message_dict})
        
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"last_message": message_dict}})
    
    def save_last_notification(self, user_id):
        time = datetime.datetime.now(tz=pytz.timezone('Israel'))
        self.usersCollection.update_one({"_id": user_id}, {"$set": {"last_notification_time": time}})
        self.notificationsCollection.insert_one({'user_id': user_id, 'time': time})
    def fix_1400_time(self):
        # 
        datetime_9am = datetime.datetime.now(tz=pytz.timezone('Israel'))
        # set the time to 9 am
        datetime_9am = datetime_9am.replace(hour=9, minute=0, second=0, microsecond=0)
        # if the time already passed, add a day
        if datetime_9am > datetime.datetime.now(tz=pytz.timezone('Israel')):
            datetime_9am += datetime.timedelta(days=1)


        # find rhe messages that were sent to string '14:00'
        users_with_old_notifycation_settings = self.usersCollection.find({'preferences.notification_time': '14:00'})
        for usr in users_with_old_notifycation_settings:
            # update the time to be 09:00:00
            self.usersCollection.update_one({'_id': usr['_id']}, {'$set': {'preferences.notification_time': datetime_9am}})
    def get_users_to_be_notified(self):
        # current time in Israel
        tz = pytz.timezone('Israel')
        current_time = datetime.datetime.now(tz)
        hh_mm_str = current_time.strftime("%H:%M")
        # find all users that the preferences.notification_time == hh_mm_str
        # make sure that passed at least preferences.send_notification_if_user_dont_send_info_for (06:00 = 6 hours) from the last notification sent to the user
        # make sure that passed at least preferences.send_notification_if_user_dont_send_info_for (06:00 = 6 hours) from the messsage the user sent
        
        # find all the users that the next_notification_time passed
        users_to_be_notified = self.usersCollection.find({'next_notification_time': {'$lte': current_time}})
        # preferd_notification_offset = int(user.get('preferences').get('send_notification_if_user_dont_send_info_for', 3600))
        # last_message = user.get('last_message')
        # ret = []
        # if not last_message is None:
        #     last_message_time = datetime.datetime.fromtimestamp(last_message.get('date'),tz=pytz.timezone('Israel')) # 1658747585
        #     secounds_pasted_from_last_message = (current_time - last_message_time).total_seconds()
        #     #prefered_secounds_passed =
        #     if  secounds_pasted_from_last_message < preferd_notification_offset:
        #         continue
        #     ret.append(user)
        # else:
        #     ret.append(user)
        #return ret
        return users_to_be_notified
        # users =  self.usersCollection.with_options(codec_options=CodecOptions(tz_aware=True,tzinfo=pytz.timezone('Israel'))).find({"preferences.notification_time": hh_mm_str,})# "preferences.send_notification_if_user_dont_send_info_for": {"$gte": self.get_last_notification_time(user_id)}})
        # ret = []
        # for user in users:
        #     # check last notification time
        #     preferd_notification_offset = int(user.get('preferences').get('send_notification_if_user_dont_send_info_for'))
        #     last_notification_time = user.get('last_notification_time')
        #     if not last_notification_time is None:
        #         #last_notification_time = datetime.datetime.strptime(last_notification_time, '%Y-%m-%d %H:%M:%S.%f')
        #         #last_notification_time = last_notification_time.replace(tzinfo=pytz.timezone('Israel'))
        #         secounds_pasted_from_last_notification = (current_time - last_notification_time).total_seconds()
        #         #prefered_secounds_pasted = user.get('preferences').get('send_notification_if_user_dont_send_info_for'):
        #         if  secounds_pasted_from_last_notification < preferd_notification_offset:
        #             continue
            
        #     last_message = user.get('last_message')
        #     if not last_message is None:
                
        #         last_message_time = datetime.datetime.fromtimestamp(last_message.get('date'),tz=pytz.timezone('Israel')) # 1658747585
        #         secounds_pasted_from_last_message = (current_time - last_message_time).total_seconds()
        #         #prefered_secounds_passed = 
        #         if  secounds_pasted_from_last_message < preferd_notification_offset:
        #             continue
        #     ret.append(user)
        #     # check last message time
        # return ret