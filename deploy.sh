#! /bin/bash
git pull
cd /home/ubuntu/clean-python-telegram-bot/
source ./env/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart telegramSupervisorConf