import paramiko
import time
import datetime
import json
import schedule
from tqdm import tqdm
import os
from pathlib import Path
import sys
from scp import SCPClient
import dropbox

def get_time():
    now = datetime.datetime.now()
    now = now.strftime("%H:%M:%S")
    
    return now

def logging(log):
    print(log)
    with open('./temp/log.txt', 'a') as f:
        f.write(log)

def createSSHClient(server, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, username, password)
    return client

def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

def scheduling(time_set, src_dir_list, dst_dir):
    repeat_type = time_set['REPEAT_TYPE']
    clock = time_set['SCHEDULE_SETTING']
    if repeat_type == 'day':
        schedule.every().day.at(clock).do(lambda: job(src_dir_list, dst_dir))
    elif repeat_type == 'hour':
        schedule.every(clock).hours.do(lambda: job(src_dir_list, dst_dir))
    elif repeat_type == 'minute':
        schedule.every(clock).minutes.do(lambda: job(src_dir_list, dst_dir))
    else:
        logging(f'\nWrong repeat type({repeat_type}).\nrepeat_type must be in ["day", "hour", "minute"]\n')
        quit()

    while True:
        schedule.run_pending()
        time.sleep(1)
    
def job(today, config, src_dir_list:list, dst_dir_list:list):
    # ssh connect
    logging(f'\n------{today}------\n')
    logging(f'\nTry to log in {config["USER_NAME"]}@{config["HOST_IP"]}..\n')

    while(True):
        try:
            ssh = createSSHClient(config['HOST_IP'], port=config['CONN_PORT'], username=config['USER_NAME'], password=config['PASSWORD'])
            break
        except:
            logging(f'\nConnection failed... Retrying in 30 seconds.\nLocal time: {get_time()}\n')
            time.sleep(30)

    logging(f'\n**Connection Successed!**\nLocal time: {get_time()}\n')

    scp = SCPClient(ssh.get_transport(), progress=progress)
    
    for i in range(len(src_dir_list)):
        start = time.time()
        _, stdout, _ = ssh.exec_command(f'ls {src_dir_list[i]}/{today}*')
        result = stdout.read().split()
        for per_result in result:
            scp.get(per_result, dst_dir_list[i], recursive=True)
        logging(f'"\n{src_dir_list[i]}" has been downloaded. (elapsed time: {time.time() - start})\nLocal time: {get_time()}\n')
    
    scp.close()        
    ssh.close()
    
    # Using Dropbox API
    dbx = dropbox.Dropbox(oauth2_access_token=config["ACCESS_KEY"],
                     oauth2_refresh_token=config["REFRESH_TOKEN"],
                        app_key=config['APP_KEY'],
                        app_secret=config['APP_SECRET'])
    
    data_dir = "./temp/"
    dropbox_destination = "/CO2/"
    
    # enumerate local files recursively
    logging(f'\nUploading the data to DropBox...\nLocal time: {get_time()}\n')
    
    for root, _, files in tqdm(os.walk(data_dir)):

        for filename in files:

            # construct the full local path
            local_path = os.path.join(root, filename)

            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, data_dir)
            dropbox_path = os.path.join(dropbox_destination, relative_path)

            # upload the file
            with open(local_path, "rb") as f:
                try:
                    dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                except:
                    print(f'\nUpload failed... Retrying in 3 seconds.\nLocal time: {get_time()}\n')
                    time.sleep(3)
                    
    print(f"\nData successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nLocal time: {get_time()}\n")
    
if __name__ == '__main__':
    
    # for time logging
    today = datetime.date.today()
    
    # get the path to the file within the executable
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    time_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_set.json')
    temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp/log.txt')
    
    # load configurations
    with open(config_path, 'r') as f:
        config = json.load(f)
        config = config['DEFAULT']

    with open(time_path, 'r') as f:
        time_set = json.load(f)
        time_set = time_set['DEFAULT']
        
    src_dir_list=[f'data/summaries', f'data/raw/{today.year}/{str(today.month).zfill(2)}']
    dst_dir_list=['./temp/summaries/', f'./temp/raw/{today.year}/{str(today.month).zfill(2)}/']
    
    for dst_dir in dst_dir_list:
        path = Path(dst_dir)
        path.mkdir(parents=True, exist_ok=True)
    
    # scheduling(time_set, src_dir_list, dst_dir_list)
    job(today, config, src_dir_list, dst_dir_list)