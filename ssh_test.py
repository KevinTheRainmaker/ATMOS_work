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
# import dropbox
import zipfile
import chardet
import csv
import logging

# get relative path to access external files
def get_relative_path(file_name):
    if getattr(sys, 'frozen', False):  
        # when packaged as an executable
        relative_path = os.path.dirname(sys.executable)
    else:
        # when run directly as a script
        relative_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(relative_path, file_name)

def env_setting(data_path: str):    
    # # load configurations
    config_path = get_relative_path('config.json')
    time_path = get_relative_path('time_set.json')

    # add environment variables for access
    os.environ['CONFIG_PATH'] = config_path
    os.environ['TIME_PATH'] = time_path
    os.environ['DATA_PATH'] = data_path
    os.makedirs(data_path, exist_ok=True)

    # set log file
    logging.basicConfig(filename='ATMOS_Bot.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# return current time in hour:month:second form
def get_time():
    now = datetime.datetime.now()
    now = now.strftime("%H:%M:%S")
    return now

# logging the intermediate results
# def logging(log):
#     data_dir = os.getenv('DATA_DIR', 'data')
#     log_path = os.getenv('LOG_PATH')
#     print(log)
#     with open(log_path, 'a') as f:
#         f.write(log)

def elapsed_time(elapsed_seconds):
    elapsed_minutes = int(elapsed_seconds // 60)
    elapsed_seconds = int(elapsed_seconds % 60)

    elapsed_time_formatted = f"{elapsed_minutes:02d}:{elapsed_seconds:02d}"
    
    return elapsed_time_formatted

# convert GHG format to CSV format
# if translation failed, return GHG file name
def ghg_to_csv(zip_file):
    base_path = os.path.dirname(zip_file)
    base_name = os.path.path.basename(zip_file)

    data_file = base_name
    data_file = data_file.replace('ghg','data')
    data_path = os.path.join(base_path, data_file)

    csv_file = base_name
    csv_file = csv_file.replace('ghg','csv')
    csv_path = os.path.join('./temp', 'csv')
    csv_path = os.path.join(csv_path, csv_file)
    
    try:
        # extract .data file from .ghg
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extract(data_file, path=str(base_path))
            
        if not os.path.exists(csv_path):
                
            # detect encoding of the .data file
            with open(data_path, 'rb') as file:
                result = chardet.detect(file.read())
            
            encoding = result['encoding']

            # read data file and write to csv
            with open(data_path, 'r', encoding=encoding) as data_form, open(csv_path, 'w', newline='', encoding='utf-8') as csv_form:
                writer = csv.writer(csv_form)

                for line in data_form:
                    line = line.strip()

                    if line.startswith('#') or not line:
                        continue

                    data = line.split('\t')

                    writer.writerow(data)
        else:
            pass
    except:
        # return the name of ghg file if translation failed
        failed = os.path.path.basename(zip_file)
        return failed

# def zip_csv_dir(directory, today):
#     # zip file name
#     zip_filename = f"{directory}/{today}_csv.zip"

#     # create temporal directory to contain csvs
#     temp_directory = f"{directory}/csv_temp"
#     os.makedirs(temp_directory, exist_ok=True)

#     # seraching the files in directory
#     for filename in os.listdir(directory):
#         filepath = os.path.join(directory, filename)
        
#         # check the prior
#         if filename.startswith(str(today)):
#             # move the files into temporal directory
#             shutil.move(filepath, temp_directory)

#     # compress temporal directory
#     if len(os.listdir(temp_directory)) == 0:
#         print('###WARNING###\nCSV folder is empty')
#     else:
#         shutil.make_archive(zip_filename, "zip", temp_directory)

#     # delete temporal directory
#     shutil.rmtree(temp_directory)

# SSH Client for connection test
# server, port, username and password are saved in the config.json
def createSSHClient(server, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, username, password)
    return client

# visualize progress status for scp download
def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

# def move_folder_contents_to_team_account(folder_path, team_email, access_token):
#     try:
#         # Dropbox 인증
#         dbx = dropbox.Dropbox(access_token)

#         # 공유 폴더 내용 가져오기
#         folder_entries = dbx.files_list_folder(folder_path).entries

#         # 각 파일을 팀 계정으로 이동시키기
#         for entry in folder_entries:
#             if isinstance(entry, dropbox.files.FileMetadata):
#                 file_path = entry.path_lower
#                 file_name = file_path.split('/')[-1]
#                 new_path = '/{}'.format(file_name)

#                 # 파일 이동
#                 dbx.files_move(file_path, new_path, allow_shared_folder=True)

#                 # 팀 계정으로 공유 설정
#                 sharing_settings = dropbox.sharing.SharedLinkSettings(team_member_only=True)
#                 shared_link = dbx.sharing_create_shared_link(new_path)
#                 dbx.sharing_add_folder_member(shared_link.url, team_email, settings=sharing_settings)

#         print("파일들이 성공적으로 팀 계정으로 이동되었습니다.")

#     except AuthError as e:
#         print("드롭박스 API 인증에 실패했습니다.")
#         print(e)

# main function of automation
# detailed explanation can be found in README.md
def job(time_buffer, config):
    
    # for time logging
    today = datetime.date.today()
    raw_results = []

    # source directories (server)
    src_dir = 'data'
    
    # destination directories (local)
    dst_dir = 'temp'

    # ssh connection test
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

    # create scp client
    scp = SCPClient(ssh.get_transport(), progress=progress)
    
    date_list = [str(today)]

    for i in range(int(time_buffer)):
        date = today - datetime.timedelta(days=i+1)
        date_list.append(str(date))

    start = time.time()

    # make destination directories at local
    sum_dir = Path(os.path.join(dst_dir, 'summaries'))
    sum_dir.mkdir(parents=True, exist_ok=True)

    for date_ent in date_list:
        year, month, _ = date_ent.split('-')
        scp.get(f"{src_dir}/summaries/{date_ent}_AIU-1905_EP-Summary.txt", os.path.join(dst_dir, 'summaries'), recursive=True)
        

        command_raw = f'ls {src_dir}/raw/{str(year)}/{str(month)}/{str(date_ent)}*'
        _, stdout, _ = ssh.exec_command(command_raw)
        output_raw = stdout.read().split()
        raw_results.extend(output_raw)
    
    elapsed_seconds = time.time() - start
    elapsed_time_formatted = elapsed_time(elapsed_seconds)
    
    logging(f'\n"summaries" has been downloaded to "{dst_dir}". (elapsed time: {elapsed_time_formatted})\nLocal time: {get_time()}\n')
    
    for raw_file_ent in raw_results:
        # print(raw_file_ent)
        raw_file = os.path.path.basename(raw_file_ent)  # Extract file name

        csv_file = raw_file.decode('utf-8').replace('.ghg', '.csv')

        csv_filepath = os.path.join(dst_dir, 'raw', 'csv', str(csv_file))  # Convert to the same type and join paths


        # get the path to the file within the executable
        csv_path = get_relative_path(str(os.path.join('temp','csv')))

        # create csv directory
        csv_path = Path(csv_path)
        csv_path.mkdir(parents=True, exist_ok=True)

        # skip downloading if csv is already exists
        if not os.path.exists(csv_filepath):
            year, month, _, _ = str(raw_file.decode('utf-8')).split('-')
            local_raw_path = os.path.join(dst_dir, 'raw',str(year), str(month))
            raw_dir = Path(local_raw_path)
            raw_dir.mkdir(parents=True, exist_ok=True)
            scp.get(f"{src_dir}/raw/{str(year)}/{str(month)}/{str(raw_file.decode('utf-8'))}", os.path.join(local_raw_path), recursive=True)

    elapsed_seconds = time.time() - start
    elapsed_time_formatted = elapsed_time(elapsed_seconds)

    logging(f'\n"raw" has been downloaded to "{dst_dir}". (elapsed time: {elapsed_time_formatted})\nLocal time: {get_time()}\n')
    
    # close the connections
    scp.close()        
    ssh.close()

    # convert ghg to csv
    local_raw_dir = './temp/raw'
    logging(f'\nTranslating ghg to csv...\nLocal time: {get_time()}\n')
    
    start = time.time()
    failed_list = []

    # Perform conversion for all files in the path
    for root, _, files in os.walk(local_raw_dir):
        for file in tqdm(files):
            if file.endswith('.ghg'):
                zip_file = os.path.join(root, file)

                result = ghg_to_csv(zip_file)
                
                # if conversion is not successed
                if (result != None):
                    failed_list.append(result)
    
    elapsed_seconds = time.time() - start
    elapsed_time_formatted = elapsed_time(elapsed_seconds)

    logging(f'\nGHG has been converted. (elapsed time: {elapsed_time_formatted})\nLocal time: {get_time()}\n')
    logging(f'\nThese are the failed list: {failed_list}\n')

    # target_formats = ['.data', '.ghg']  # format to delete
    target_formats = ['.data']

    for filename in os.listdir(dst_dir):
        for target_format in target_formats:
            # delete the target format files if it didn't exists on the failed list
            if filename.endswith(target_format) and filename not in failed_list: 
                file_path = os.path.join(local_raw_dir, filename)
                os.remove(file_path)

    # csv_path = f'{dst_dir_list[i]}/csv'
    # zip_csv_dir(csv_path, today)

    ##################THIS PART HAS BEEN DEPRICATED SINCE THE CLIENT'S NEEDS CHANGED################
    """
    # Using Dropbox API
    # ACCESS_KEY, REFRESH_TOKEN, APP_KEY and APP_SECRET are saved in the config.json
    dbx = dropbox.Dropbox(oauth2_access_token=default_config["ACCESS_KEY"],
                     oauth2_refresh_token=default_config["REFRESH_TOKEN"], # to refresh the Access Token
                        app_key=default_config['APP_KEY'],
                        app_secret=default_config['APP_SECRET'])
    
    # data path in local
    temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    data_dir = os.environ.get('DATA_DIR', temp_path)
    
    # data path at dropbox
    dropbox_destination = os.environ.get('DROPBOX_DESTINATION', '/CO2')

    # enumerate local files recursively
    logging(f'\nUploading the data to DropBox...\nLocal time: {get_time()}\n')
    
    for root, _, files in os.walk(data_dir):
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
                while(True):
                    try:
                        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                        break
                    except dropbox.exceptions.ApiError:
                        # if API error occured, retry it in 3 seconds
                        # if the error occured continnuously, please let me know
                        logging(f'\nUpload failed... Retrying in 3 seconds.\nLocal time: {get_time()}\n')
                        time.sleep(3)

    logging(f"\nData successfully uploaded to dropbox. (saved directory: {dropbox_destination})\nLocal time: {get_time()}\n")
    """
    ################################################################################################
    
    os.system('cls') # clear the console output

# scheduling for automation
def scheduling(config, time_set):
    repeat_type = time_set['REPEAT_TYPE']
    clock = time_set['SCHEDULE_SETTING']
    time_buffer = time_set['TIME_BUFFER']
    print(repeat_type)
    print(clock)
    quit()
    if repeat_type == 'day':
        schedule.every().day.at(clock).do(lambda: job(time_buffer, config))
    elif repeat_type == 'hour':
        schedule.every(int(clock)).hours.do(lambda: job(time_buffer, config))
    elif repeat_type == 'minute':
        schedule.every(int(clock)).minutes.do(lambda: job(time_buffer, config))
    else:
        logging(f'\nWrong repeat type({repeat_type}).\nrepeat_type must be in ["day", "hour", "minute"]\n')
        quit()
    
    # for checking whether the process is stopped
    animation = '\|/-'

    while True:
        # pending the process until the next scheduled time
        schedule.run_pending()

        next_run = schedule.next_run()
        formatted_next_run = next_run.strftime('%Y-%m-%d %H:%M')
        
        for i in range(12):
            time.sleep(0.15)
            print(f'\rThe download will be started at {formatted_next_run}  {animation[i % len(animation)]}', end="")

# read json file
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def get_json_data(config_path: str):
    with open(config_path, 'r', encoding='utf-8') as f:
        contents = f.read()
        while "/*" in contents:
            preComment, postComment = contents.split('/*', 1)
            contents = preComment + postComment.split('*/', 1)[1]
        json_data = json.loads(contents.replace("'", '"'))
        return json_data['DEFAULT']

if __name__ == '__main__':
    env_setting('./temp')
    
    config = os.getenv('CONFIG_PATH')
    time_set = get_json_data(os.getenv('TIME_PATH'))
    
    # start scheduling
    scheduling(config, time_set)