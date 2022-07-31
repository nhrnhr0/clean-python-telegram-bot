
import threading
import time
import asyncio
import json
import pytz
import datetime
from db import MongoDB
from myLogger import logger
def notification_thread_caller(bot,):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(notification_thread(bot))
    loop.close()
async def notification_thread(bot):
    from telegramManager import send_nofication
    db = MongoDB().getInstance()
    while True:
            time.sleep(5)
            try:
                logger.info('running notification thread loop')
                db.fix_1400_time()
                allDbUsersToBeNotifyed = db.get_users_to_be_notified()
                for dbUser in allDbUsersToBeNotifyed:
                    # if the users already sent us data in the last send_notification_if_user_dont_send_info_for (secounds) we will not send him again, so we will update thier next_notification_time.
                    last_message = dbUser.get('last_message', None)
                    if last_message is not None:    
                        time_from_last_message_secounds = time.time() - last_message['date']
                        user_prefered_offset_secounds = int(dbUser.get('send_notification_if_user_dont_send_info_for',3600))
                        if time_from_last_message_secounds < user_prefered_offset_secounds:
                            db.update_user_next_notification_time(dbUser['_id'], db.recalculate_next_notification_time(dbUser))
                            continue
                    
                    last_notification = dbUser.get('last_notification_time', None)
                    
                    if last_notification is not None:
                        last_notification = last_notification.replace(tzinfo=pytz.utc)
                        #time_from_last_notification_secounds = time.time() - last_notification
                        #last_notification_timestemp = datetime.datetime.strptime(last_notification, "%Y-%m-%d %H:%M:%S.%f")
                        time_from_last_notification = datetime.datetime.now(tz=pytz.utc) - last_notification
                        user_prefered_offset_secounds = int(dbUser.get('send_notification_if_user_dont_send_info_for',3600))
                        dont_disturbe_for = datetime.timedelta(seconds=user_prefered_offset_secounds)
                        if time_from_last_notification < dont_disturbe_for:
                            db.update_user_next_notification_time(dbUser['_id'], db.recalculate_next_notification_time(dbUser))
                            continue
                    
                    # should_send_nofication = True
                    # notification_time = dbUser.get('notification_time', None)
                    # if notification_time != time.strftime("%H:%M"):
                    #     should_send_nofication=False
                    # else:
                    #     last_message = None
                    #     last_message = dbUser.get('last_message', None)
                    #     if last_message is not None:
                            
                    #         time_from_last_message_secounds = time.time() - last_message['date']
                    #         user_prefered_offset_secounds = int(dbUser['send_notification_if_user_dont_send_info_for'].split(':')[0]) * 60 + int(dbUser['send_notification_if_user_dont_send_info_for'].split(':')[1]) * 60
                    #         if time_from_last_message_secounds < user_prefered_offset_secounds:
                    #             should_send_nofication = False

                    #     last_notification = None
                    #     last_notification = dbUser.get('last_notification', None)
                    #     if last_notification is not None:
                    #         # convenrt last_notification to datetime
                    #         last_notification_timestemp = datetime.datetime.strptime(last_notification, "%Y-%m-%d %H:%M:%S.%f")
                    #         time_from_last_notification = datetime.datetime.now() - last_notification_timestemp
                    #         user_prefered_offset_secounds = datetime.timedelta(minutes=int(dbUser['send_notification_if_user_dont_send_info_for'].split(':')[0]) * 60 + int(dbUser['send_notification_if_user_dont_send_info_for'].split(':')[1]))
                    #         if time_from_last_notification < user_prefered_offset_secounds:
                    #             should_send_nofication = False
                        
                        
                    # if should_send_nofication:
                    try:
                        await send_nofication(bot, dbUser)
                        
                    except Exception as e:
                        logger.error(e)
                        pass
                    # reminder_time = current time + 1 hour (timezone Israel)
                    reminder_time = datetime.datetime.now(tz=pytz.timezone('Israel')) + datetime.timedelta(hours=1)

                    db.set_reminder_time(dbUser['_id'], reminder_time)
                    db.update_user_next_notification_time(dbUser['_id'], db.recalculate_next_notification_time(dbUser))
                    #db.recalculate_next_notification_time(dbUser)
                    #logger.info(f"Notification checked for {dbUser['username']}")
                
                allDbUsersToBeReminded = db.get_users_to_be_reminded()
                for user in allDbUsersToBeReminded:
                    print(user)
                #print(len(allDbUsersToBeReminded))
            except Exception as e:
                logger.error(f"Error in notification thread: {e}")
                continue
            
            