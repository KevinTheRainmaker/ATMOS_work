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
import zipfile
import chardet
import csv
import logging
import multiprocessing
from multiprocessing import Process
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
    sum_path = os.path.join(data_path, 'summaries')
    csv_path = os.path.join(data_path, 'csv')
    
    # add environment variables for access
    os.environ['CONFIG_PATH'] = config_path
    os.environ['TIME_PATH'] = time_path
    os.environ['DATA_PATH'] = data_path
    os.environ['SUM_PATH'] = sum_path
    os.environ['CSV_PATH'] = csv_path
    os.makedirs(data_path, exist_ok=True)
    os.makedirs(sum_path, exist_ok=True)
    os.makedirs(csv_path, exist_ok=True)

    # set log file
    logging.basicConfig(filename='ATMOS_Bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    return get_json_data(config_path), get_json_data(time_path)

def elapsed_time(elapsed_seconds):
    elapsed_minutes = int(elapsed_seconds // 60)
    elapsed_seconds = int(elapsed_seconds % 60)

    elapsed_time_formatted = f"{elapsed_minutes:02d}:{elapsed_seconds:02d}"
    
    return elapsed_time_formatted

def logging_info(log):
    logging.info(log)
    print(log)

def extract_data(ghg_path):
    base_path = os.path.dirname(ghg_path)
    ghg_file = os.path.basename(ghg_path)
    data_file = ghg_file.replace('.ghg', '.data')

    try:
        # extract .data file from .ghg
        with zipfile.ZipFile(ghg_path, 'r') as zip_ref:
                zip_ref.extract(data_file, path=str(base_path))
    except:
        failed = os.path.basename(ghg_file)
        return failed

# convert GHG format to CSV format
# if translation failed, return GHG file name
def data_to_csv(data_file):
    base_path = os.path.dirname(data_file)
    data_path = os.path.join(base_path, data_file)

    csv_file = os.path.basename(data_file)
    csv_file = csv_file.replace('data','csv')
    csv_path = os.getenv('CSV_PATH')
    csv_path = os.path.join(csv_path, csv_file)
    
    try:
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
    except:
        # return the name of ghg file if translation failed
        failed = os.path.basename(data_file)
        return failed

# SSH Client for connection test
# server, port, username and password are saved in the config.json
def test_ssh_connection(hostname, port, username, password):
    logging_info(f'Try to log in {username}@{hostname}..')
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password)
        logging_info("SSH connection successful!")
        client.close()
        return True
    except paramiko.AuthenticationException:
        logging.critical("Authentication failed.")
        return False
    except paramiko.SSHException as e:
        logging.error("SSH connection failed:", str(e))
        return False
    except Exception as e:
        logging.error("An error occurred:", str(e))
        return False

# visualize progress status for scp download
def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

def get_date_list(time_buffer):
    today = datetime.date.today()
    date_list = [str(today)]

    for i in range(int(time_buffer)):
        date = today - datetime.timedelta(days=i+1)
        date_list.append(str(date))

    return date_list

def get_download_list(args):
    hostname, port, username, password, date = args
    year, month, _ = date.split('-')
    
    raw_results = []
    sum_results = []
    
    raw_path = f"data/raw/{str(year)}/{str(month)}"
    sum_path = f'data/summaries'

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    command_raw = f'ls {raw_path}/{str(date)}*.ghg'
    _, stdout, _ = ssh.exec_command(command_raw)
    output_raw = stdout.read().split()
    
    command_sum = f'ls {sum_path}/{str(date)}*.txt'
    _, stdout, _ = ssh.exec_command(command_sum)
    output_sum = stdout.read().split()
    
    raw_results.extend(output_raw)
    sum_results.extend(output_sum)
    
    return year, month, raw_results, sum_results

def download_file(args):
    hostname, port, username, password, _ = args
    dst_dir = os.getenv('DATA_PATH')
    
    raw_results = []
    sum_results = []
    
    year, month, raw_results, sum_results = get_download_list(args)
    
    local_raw_path = os.path.join(dst_dir, 'raw',str(year), str(month))
    local_sum_path = os.path.join(dst_dir, 'summaries')
    
    for raw_file_ent in raw_results:
        # print(raw_file_ent)
        # raw_file = os.path.basename(raw_file_ent)  # Extract file name
        raw_dir = Path(local_raw_path)
        raw_dir.mkdir(parents=True, exist_ok=True)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password, timeout=120)
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            # while(True):
            #     try:
            #         scp.get(f"{raw_file_ent}", os.path.join(local_raw_path), recursive=True)
            #         break
            #     except multiprocessing.TimeoutError:
            #         logging_info('Time out Occured.. Retry in 1 sec.')
            #         time.sleep(1)
            # scp.get(f"{remote_path}/{str(raw_file.decode('utf-8'))}", os.path.join(local_raw_path), recursive=True)
            scp.get(f"{raw_file_ent.decode('utf-8')}", os.path.join(local_raw_path), recursive=True)
        ssh.close()

    for sum_file_ent in sum_results:
        # print(sum_file_ent)
        # raw_file = os.path.basename(sum_file_ent)  # Extract file name
        sum_dir = Path(local_sum_path)
        sum_dir.mkdir(parents=True, exist_ok=True)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password, timeout=120)
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            # while(True):
            #     try:
            #         scp.get(f"{sum_file_ent}", os.path.join(local_sum_path), recursive=True)
            #         break
            #     except multiprocessing.TimeoutError:
            #         logging_info('Time out Occured.. Retry in 1 sec.')
            #         time.sleep(1)
            # scp.get(f"{remote_path}/{str(raw_file.decode('utf-8'))}", os.path.join(local_sum_path), recursive=True)
            scp.get(f"{sum_file_ent.decode('utf-8')}", os.path.join(local_sum_path), recursive=True)
        ssh.close()
# main function of automation
# detailed explanation can be found in README.md
def job(time_buffer):
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

    print(f'"summaries" has been downloaded to "{dst_dir}". (elapsed time: {elapsed_time_formatted})\n')
    
    processes = []
    grouped_files = {}

    for remote_file in remote_files:
        remote_directory = os.path.dirname(remote_file)
        if remote_directory not in grouped_files:
            grouped_files[remote_directory] = []
        grouped_files[remote_directory].append(remote_file)

    for remote_directory, files in grouped_files.items():
        local_directory = os.path.join(local_dir, remote_directory.lstrip('/'))
        os.makedirs(local_directory, exist_ok=True)

        process_args = (hostname, username, password, remote_directory, local_directory)
        process = multiprocessing.Process(target=download_worker, args=(process_args,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

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

    print(f'\n"raw" has been downloaded to "{dst_dir}". (elapsed time: {elapsed_time_formatted})\n')
    
    # close the connections
    scp.close()        
    ssh.close()

    # convert ghg to csv
    local_raw_dir = './temp/raw'
    print(f'\nTranslating ghg to csv...\nLocal time: {get_time()}\n')
    
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

    print(f'\nGHG has been converted. (elapsed time: {elapsed_time_formatted})\n')
    print(f'\nThese are the failed list: {failed_list}\n')

    # target_formats = ['.data', '.ghg']  # format to delete
    target_formats = ['.data']

    for filename in os.listdir(dst_dir):
        for target_format in target_formats:
            # delete the target format files if it didn't exists on the failed list
            if filename.endswith(target_format) and filename not in failed_list: 
                file_path = os.path.join(local_raw_dir, filename)
                os.remove(file_path)

    os.system('cls') # clear the console output

def job(config, time_buffer):    
    hostname = config['HOST_IP']
    port=config['CONN_PORT']
    username=config['USER_NAME']
    password=config['PASSWORD']
    failed_dict = {
        'Extraction Failed':[],
        'Conversion Failed':[]
        }
    
    connect_flag = False
    while(connect_flag == False):
        connect_flag = test_ssh_connection(hostname, port, username, password)
        time.sleep(10)
    
    date_list = get_date_list(time_buffer)
    # num_processes = multiprocessing.cpu_count()
    # logging_info(f'Usable CPU Cores: {num_processes}')
    
    # chunk_size = max(int(time_buffer)//int(num_processes), int(num_processes))
    # logging_info(f'Chunk Size: {chunk_size}')
    for date in date_list:
        download_file([hostname, port, username, password, date])
    # for date in date_list:
    #     p = Process(target=download_file, args=[(hostname, port, username, password, date)])
    #     p.start()
    #     p.join()
    # with multiprocessing.Pool(processes=num_processes) as pool:
    #     pool.map(download_file, [(hostname, port, username, password, date) for date in date_list], chunk_size)
    logging_info('Download is Done')
    
    # Perform conversion for all files in the path
    for root, _, files in os.walk(os.getenv('DATA_PATH')):
        for file in tqdm(files):
            if file.endswith('.ghg'):
                ghg_file = os.path.join(root, file)

                extraction_fail = extract_data(ghg_file)
                if (extraction_fail != None):
                    failed_dict['Extraction Failed'].append(extraction_fail)
            if file.endswith('.data'):
                data_file = os.path.join(root, file)
                conversion_fail = data_to_csv(data_file)
                # if conversion is not successed
                if (conversion_fail != None):
                    failed_dict['Conversion Failed'].append(conversion_fail)
    logging_info('Conversion is Done.')
    logging_info(f'Failed List: {[i for i in failed_dict.items()]}')

# scheduling for automation
def scheduling():
    config, time_set = env_setting('./temp')
    
    repeat_type = time_set['REPEAT_TYPE']
    clock = time_set['SCHEDULE_SETTING']
    time_buffer = time_set['TIME_BUFFER']

    if repeat_type == 'day':
        schedule.every().day.at(clock).do(lambda: job(config, time_buffer))
    elif repeat_type == 'hour':
        schedule.every(int(clock)).hours.do(lambda: job(config, time_buffer))
    elif repeat_type == 'minute':
        schedule.every(int(clock)).minutes.do(lambda: job(config, time_buffer))
    else:
        logging.critical(f'\nWrong repeat type: {repeat_type}')
        print(f'\nWrong repeat type({repeat_type}).\nrepeat_type must be in ["day", "hour", "minute"]\n')
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
    config, time_set = env_setting('./temp')
    time_buffer = time_set['TIME_BUFFER']
    
    job(config, time_buffer)
    # start scheduling
    # scheduling(time_set)
    # check_ssh_connect(config)