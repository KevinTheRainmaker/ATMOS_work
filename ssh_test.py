import paramiko
import time
import datetime
import json
import schedule
import os
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

def scheduling(clock, src_dir_list, dst_dir):
    schedule.every().day.at(clock).do(lambda: job(src_dir_list, dst_dir))

    while True:
        schedule.run_pending()
        time.sleep(3)

def job(today, src_dir_list:list, dst_dir_list:list):
    path = './temp'
    if not os.path.isdir(path):
        os.mkdir(path)
    
    # load configurations
    with open('./config.json', 'r') as f:
        config = json.load(f)
        config = config['DEFAULT']

    # ssh connect
    logging(f'------{today}------\n')
    logging(f'Try to log in {config["USER_NAME"]}@{config["HOST_IP"]}..\n')

    while(True):
        try:
            ssh = createSSHClient(config['HOST_IP'], port=config['CONN_PORT'], username=config['USER_NAME'], password=config['PASSWORD'])
            break
        except:
            logging(f'Connection failed... Retrying in 30 seconds.\nLocal time: {get_time()}\n')
            time.sleep(30)

    logging(f'\n**Connection Successed!**\nLocal time: {get_time()}\n')

    scp = SCPClient(ssh.get_transport(), progress=progress)
    
    for i in range(len(src_dir_list)):
        start = time.time()
        scp.get(src_dir_list[i], dst_dir_list[i], recursive=True)
        logging(f'"{src_dir_list[i]}" has been downloaded. (elapsed time: {time.time() - start})\nLocal time: {get_time()}\n')
        
    ssh.close()

    # Using Dropbox API
    dbx = dropbox.Dropbox(config['ACCESS_KEY'])
    
    data_dir = "./temp/"
    dropbox_destination = "/CO2/"
    
    # enumerate local files recursively
    for root, dirs, files in os.walk(data_dir):

        for filename in files:

            # construct the full local path
            local_path = os.path.join(root, filename)

            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, data_dir)
            dropbox_path = os.path.join(dropbox_destination, relative_path)

            # upload the file
            with open(local_path, "rb") as f:
                try:
                    logging(f'Trying to upload the data to DropBox...\nLocal time: {get_time()}\n')
                    dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                except:
                    logging(f'Upload failed... Retrying in 30 seconds.\nLocal time: {get_time()}\n')
                    time.sleep(30)
                    
    logging(f"Data successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nLocal time: {get_time()}\n")

if __name__ == '__main__':
    
    # for time logging
    today = datetime.date.today()
    
    src_dir_list=[f'data/raw/{today.year}/{str(today.month).zfill(2)}/',f'data/summaries/']
    dst_dir_list=[f'./temp/raw/{today.year}/', './temp/']
    # scheduling('09:00', src_dir_list, dst_dir_list)
    job(today, src_dir_list, dst_dir_list)