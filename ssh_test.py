import paramiko
import time
import datetime
import json
import schedule
import os
from scp import SCPClient

def logging(log):
    print(log)
    with open('./temp/log.txt', 'a') as f:
        f.write(log)

def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def job(srcfilename:list, dstfilename:str):
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
    while(True):
        try:
            ssh = createSSHClient(config['HOST_IP'], port=config['CONN_PORT'], username=config['USER_NAME'], password=config['PASSWORD'])
            break
        except:
            logging(f'Connection failed... Retrying in 30 seconds.  {now}\n')
            time.sleep(30)

    logging(f'\nConnection Successed!   {now}\n')

    scp = SCPClient(ssh.get_transport())
    scp.get(srcfilename[0],dstfilename)
    scp.get(srcfilename[1],dstfilename)
    ssh.close()

def scheduling(clock, srcfilename, dstfilename):
    schedule.every().day.at(clock).do(lambda: job(srcfilename, dstfilename))

    while True:
        schedule.run_pending()
        time.sleep(3)

if __name__ == '__main__':
    srcfilename=['data/raw', 'data/summaries']
    dstfilename='./temp/'
    # scheduling('09:00')
    job(srcfilename, dstfilename)