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
import zipfile
import chardet
import csv

os.environ['DATA_DIR'] = './temp'
os.environ['DROPBOX_DESTINATION'] = '/CO2'

def get_time():
    now = datetime.datetime.now()
    now = now.strftime("%H:%M:%S")
    
    return now

def logging(log):
    print(log)
    with open('./temp/log.txt', 'a') as f:
        f.write(log)

def ghg_to_csv(zip_file):
    base_path = os.path.dirname(zip_file)
    base_name = os.path.basename(zip_file)

    data_file = base_name
    data_file = data_file.replace('ghg','data')
    data_path = os.path.join(base_path, data_file)

    csv_file = base_name
    csv_file = csv_file.replace('ghg','csv')
    csv_path = os.path.join(base_path, 'csv')
    csv_path = os.path.join(csv_path, csv_file)
    if sys.platform == 'win32':
        csv_path = csv_path.replace('\\', '/')

    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extract(data_file, path=str(base_path))
    except:
        print(f'"{zip_file}" is not a zip file. Please check it manually.')

    with open(data_path, 'rb') as file:
        result = chardet.detect(file.read())

    encoding = result['encoding']

    with open(data_path, 'r', encoding=encoding) as data_form, open(csv_path, 'w', newline='', encoding='utf-8') as csv_form:
        writer = csv.writer(csv_form)

        for line in data_form:
            line = line.strip()

            if line.startswith('#') or not line:
                continue

            data = line.split('\t')

            writer.writerow(data)
    

def createSSHClient(server, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, username, password)
    return client

def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

<<<<<<< HEAD
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
    
=======
>>>>>>> b3be9625020c8f96ead7951c47277b6339c80244
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
<<<<<<< HEAD
        _, stdout, _ = ssh.exec_command(f'ls {src_dir_list[i]}/{today}*')
        result = stdout.read().split()
        for per_result in result:
            scp.get(per_result, dst_dir_list[i], recursive=True)
        logging(f'"\n{src_dir_list[i]}" has been downloaded. (elapsed time: {time.time() - start})\nLocal time: {get_time()}\n')
=======
        if sys.platform == 'win32':
            for j in range(len(src_dir_list)):
                src_dir_list[j] = src_dir_list[j].replace('\\', '/')

        _, stdout, _ = ssh.exec_command(f'ls {src_dir_list[i]}/{today}*')
        result = stdout.read().split()

        for per_result in result:
            filename = os.path.basename(per_result)  # Extract file name
            local_filepath = os.path.join(dst_dir_list[i], filename.decode())  # Convert to the same type and join paths

            if not os.path.exists(local_filepath):
                scp.get(per_result, dst_dir_list[i], recursive=True)

        logging(f'\n"{src_dir_list[i]}" has been downloaded. (elapsed time: {time.time() - start})\nLocal time: {get_time()}\n')
>>>>>>> b3be9625020c8f96ead7951c47277b6339c80244
    
    scp.close()        
    ssh.close()
    
    # translate ghg to csv
    # 경로 설정
    directory = 'temp/raw/2023/'
    logging(f'\nTranslating ghg to csv...\nLocal time: {get_time()}\n')
    
    start = time.time()

    # 경로 내의 모든 파일에 대해 변환 수행
    for root, _, files in os.walk(directory):
        for file in tqdm(files):
            if file.endswith('.ghg'):
                zip_file = os.path.join(root, file)

                if sys.platform == 'win32':
                    zip_file = zip_file.replace('\\', '/')

                ghg_to_csv(zip_file)
    
    logging(f'\nAll GHG has been translated. (elapsed time: {time.time() - start})\nLocal time: {get_time()}\n')

    target_format = '.data'  # 삭제할 파일 포맷

    for filename in os.listdir(dst_dir_list[1]):
        if filename.endswith(target_format):
            file_path = os.path.join(dst_dir_list[1], filename)
            os.remove(file_path)

    # Using Dropbox API
    dbx = dropbox.Dropbox(oauth2_access_token=config["ACCESS_KEY"],
                     oauth2_refresh_token=config["REFRESH_TOKEN"],
                        app_key=config['APP_KEY'],
                        app_secret=config['APP_SECRET'])
    
    temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')  
    data_dir = os.environ.get('DATA_DIR', temp_path)
    dropbox_destination = os.environ.get('DROPBOX_DESTINATION', '/CO2')

    # enumerate local files recursively
    logging(f'\nUploading the data to DropBox...\nLocal time: {get_time()}\n')
    
    for root, _, files in tqdm(os.walk(data_dir)):

        for filename in tqdm(files):

            # construct the full local path
            local_path = os.path.join(root, filename)

            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, data_dir)
            dropbox_path = os.path.join(dropbox_destination, relative_path)
            
            if sys.platform == 'win32':
                local_path = local_path.replace('\\', '/')
                dropbox_path = dropbox_path.replace('\\', '/')

            # upload the file
            with open(local_path, "rb") as f:
<<<<<<< HEAD
                try:
                    dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                except:
                    print(f'\nUpload failed... Retrying in 3 seconds.\nLocal time: {get_time()}\n')
                    time.sleep(3)
                    
    print(f"\nData successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nLocal time: {get_time()}\n")
    
=======
                while(True):
                    try:
                        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                        break
                    except dropbox.exceptions.ApiError:
                        logging(f'\nUpload failed... Retrying in 3 seconds.\nLocal time: {get_time()}\n')
                        time.sleep(3)
    logging(f"\nData successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nLocal time: {get_time()}\n")

def scheduling(time_set, src_dir_list, dst_dir_list):
    repeat_type = time_set['REPEAT_TYPE']
    clock = time_set['SCHEDULE_SETTING']
    if repeat_type == 'day':
        schedule.every().day.at(clock).do(lambda: job(today, config, src_dir_list, dst_dir_list))
    elif repeat_type == 'hour':
        schedule.every(int(clock)).hours.do(lambda: job(today, config, src_dir_list, dst_dir_list))
    elif repeat_type == 'minute':
        schedule.every(int(clock)).minutes.do(lambda: job(today, config, src_dir_list, dst_dir_list))
    else:
        logging(f'\nWrong repeat type({repeat_type}).\nrepeat_type must be in ["day", "hour", "minute"]\n')
        quit()

    while True:
        schedule.run_pending()
        time.sleep(1)

>>>>>>> b3be9625020c8f96ead7951c47277b6339c80244
if __name__ == '__main__':
    
    # for time logging
    today = datetime.date.today()

    src_dir_list=[f'data/summaries', f'data/raw/{today.year}/{str(today.month).zfill(2)}']
    dst_dir_list=['temp/summaries', f'temp/raw/{today.year}/{str(today.month).zfill(2)}']
    
    if sys.platform == 'win32':
        for i in range(len(src_dir_list)):
            src_dir_list[i] = src_dir_list[i].replace('/', '\\')
        for i in range(len(dst_dir_list)):
            dst_dir_list[i] = dst_dir_list[i].replace('/', '\\')

    for dst_dir in dst_dir_list:
        path = Path(dst_dir)
        path.mkdir(parents=True, exist_ok=True)

    csv_path = os.path.join(dst_dir_list[1], 'csv')
    csv_path = csv_path.replace('\\','/')
    csv_path = Path(csv_path)
    csv_path.mkdir(parents=True, exist_ok=True)

    # get the path to the file within the executable
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    time_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time_set.json')
<<<<<<< HEAD
    temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp/log.txt')
=======
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp/log.txt')
>>>>>>> b3be9625020c8f96ead7951c47277b6339c80244
    
    # load configurations
    with open(config_path, 'r') as f:
        config = json.load(f)
        config = config['DEFAULT']

    with open(time_path, 'r') as f:
        time_set = json.load(f)
        time_set = time_set['DEFAULT']
        
<<<<<<< HEAD
    src_dir_list=[f'data/summaries', f'data/raw/{today.year}/{str(today.month).zfill(2)}']
    dst_dir_list=['./temp/summaries/', f'./temp/raw/{today.year}/{str(today.month).zfill(2)}/']
    
    for dst_dir in dst_dir_list:
        path = Path(dst_dir)
        path.mkdir(parents=True, exist_ok=True)
    
    # scheduling(time_set, src_dir_list, dst_dir_list)
    job(today, config, src_dir_list, dst_dir_list)
=======
    # scheduling(time_set, src_dir_list, dst_dir_list)
    job(today, config, src_dir_list, dst_dir_list)
>>>>>>> b3be9625020c8f96ead7951c47277b6339c80244
