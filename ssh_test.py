import paramiko
import time
import datetime
import json
import schedule
import os

def logging(log):
    with open('./temp/log.txt', 'a') as f:
        f.write(log)

def job():
    path = './temp'
    if not os.path.isdir(path):
        os.mkdir(path)

    # for time logging
    current_date = datetime.date.today()
    current_date = current_date.strftime("%m/%d/%Y")

    now = datetime.datetime.now()
    now = now.strftime("%H:%M:%S")

    logging(f'------{current_date}------\n')

    # load configurations
    with open('./config.json', 'r') as f:
        config = json.load(f)
        config = config['DEFAULT']

    # ssh connect
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while(True):
        try:
            ssh.connect(config['HOST_IP'], port=config['CONN_PORT'], username=config['USER_NAME'], password=config['PASSWORD'])
            break
        except:
            logging(f'Connection failed... Retrying in 30 seconds.  {now}\n')
            time.sleep(30)

    logging(f'\nConnection Successed!   {now}\n')

    stdin, stdout, stderr = ssh.exec_command('cd data && ls')
    print(''.join(stdout.readlines()))

    ssh.close()

def scheduling(clock):
    schedule.every().day.at(clock).do(job)

    while True:
        schedule.run_pending()
        time.sleep(3)

if __name__ == '__main__':
    # scheduling('09:00')
    job()