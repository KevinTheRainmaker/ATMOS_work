import paramiko
import time
import datetime
import json
import schedule
import os
import sys
from scp import SCPClient
import dropbox

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

def job(src_dir_list:list, dst_dir:str):
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
    logging(f'Try to log in {config["USER_NAME"]}@{config["HOST_IP"]}..\n')

    while(True):
        try:
            ssh = createSSHClient(config['HOST_IP'], port=config['CONN_PORT'], username=config['USER_NAME'], password=config['PASSWORD'])
            break
        except:
            logging(f'Connection failed... Retrying in 30 seconds.\nserver time: {now}\n')
            time.sleep(30)

    logging(f'\n**Connection Successed!**\nserver time: {now}\n')

    scp = SCPClient(ssh.get_transport(), progress=progress)
    
    for i in range(len(src_dir_list)):
        start = time.time()
        scp.get(src_dir_list[i], dst_dir, recursive=True)
        logging(f'"{src_dir_list[i]}" has been downloaded. (elapsed time: {time.time() - start})\nserver time: {now}\n')
        
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
                dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    logging(f"Data successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nserver time: {now}\n")

if __name__ == '__main__':
    src_dir_list=['data/summaries']
    # src_dir_list=['data/raw/', 'data/summaries']
    dst_dir='./temp/'
    # scheduling('09:00', src_dir_list, dst_dir)
    job(src_dir_list, dst_dir)