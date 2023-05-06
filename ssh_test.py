import paramiko
import time
import datetime
import json

# for time logging
now = datetime.datetime.now()

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
        print('Connection failed... Retrying in 30 seconds.')
        time.sleep(30)

print(f'Connection Successed!   {now}')

stdin, stdout, stderr = ssh.exec_command('cd data && ls')
print(''.join(stdout.readlines()))

ssh.close()