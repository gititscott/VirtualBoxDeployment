
#!/usr/bin/python
import logging
import os
import re
import sys
import time
import paramiko
import getpass

def run_os_cmd(cmd, job=''):
    cmd_results = os.popen(cmd).read()
    logging.info(f'Executing:\n{cmd}\n')
    logging.info(f'Results of {job}: \n{cmd_results}')

def run_ssh_command(cmd, ssh_password):
    while True:
        try:
            logging.info(f'Attempting SSH Connection...')
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SSH_HOST, 22, username=SSH_USER, password=ssh_password) 
            logging.info(f'Executing command: {cmd}')
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
            stdin.write(ssh_password + "\n")
            stdin.flush()
            logging.info(stdout.read())
            break
        except:
            logging.error(f'Error opening SSH Session will retry in 30 seconds.')
            time.sleep(30)

destination_path = "~/VirtualBox VMs"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('VirtualBox Management, images available for deployment:')

image_dictionary = {
    "ubuntu20": "~/VirtualBoxDeployment/blank.ova"
}
image = ''

SSH_HOST = ''
SSH_USER = ''

if (len(sys.argv) == 3 or len(sys.argv) == 4):
    logging.info(f'Validating hostname {sys.argv[1]} and IP {sys.argv[2]}')
    if ( (re.match('^(?![0-9]{1,15}$)[a-zA-Z0-9-_]{1,15}$', sys.argv[1] )) and (re.match('192.168.1.\d{1,3}', sys.argv[2] ))):
        hostname = sys.argv[1] 
        ip = sys.argv[2]
        logging.info(f'{ip} and {hostname} are valid.')
    else:
        logging.error(f'Hostname and or IP Values are invalid.')
        sys.exit()
    if len(sys.argv) == 4:
        if sys.argv[3] in image_dictionary.keys():
            logging.info(f'{image} was selected from the command line and is valid.')
            image = sys.argv[3]
        else:
            logging.error(f'{sys.argv[3]} is not a valid image, user will be prompted for image name.')
else:
    print("Please provide the hostname and IP as the only two the command line arguments.")
    sys.exit()

cmd = '/usr/local/bin/VBoxManage list vms'
for machine in os.popen(cmd).read().splitlines():
    machine = machine.replace("\"", "").split()
    if machine[0] == hostname:
        logging.error(f'{hostname} already exists in the VBox Inventory.')
        sys.exit()

if not image:
    logging.info(f'Please choose an image you would like to deploy:')
    for os_name, image in image_dictionary.items():
        print(f'    {os_name} -> {image}')
    image = input("Type the image name, for example: 'ubuntu20' : ")
    if image not in image_dictionary.keys():
        logging.error(f'Image for {image} not found.')
        sys.exit()

logging.info(f'Attempting dry run of to deploy {image} with hostname {hostname} and IP {ip}')
run_os_cmd(f'VBoxManage import {image_dictionary[image]}  --vsys 0 --vmname {hostname} --vsys 0 --settingsfile "{destination_path}/{hostname}/{hostname}.vbox" --vsys 0 --unit 14 --disk "{destination_path}/{hostname}/{hostname}.vmdk" --dry-run', job='deploy_vm_dry_run')

if not input("Deploy the image? (y/n): ").lower().strip()[:1] == "y": sys.exit(1)

run_os_cmd(f'VBoxManage import {image_dictionary[image]}  --vsys 0 --vmname {hostname} --vsys 0 --settingsfile "{destination_path}/{hostname}/{hostname}.vbox" --vsys 0 --unit 14 --disk "{destination_path}/{hostname}/{hostname}.vmdk"', job='deploy_vm')
run_os_cmd(f'VBoxManage startvm {hostname} --type headless', job='start_vm')

logging.info(f'Waiting for {hostname} to start...')
time.sleep(30)

logging.info(f'Please enter the username for the image')
ssh_password  = getpass.getpass("Password:") 

run_ssh_command("sudo -k sudo hostnamectl set-hostname " + hostname, ssh_password)
run_ssh_command("sudo sed -i 's/192.168.1.5\//" + ip + "\//g' /etc/netplan/00-installer-config.yaml", ssh_password)
run_ssh_command("sudo reboot now", ssh_password)

#Update the local hosts file
logging.info(f'Adding {ip} with a {hostname} to the local hosts file.')
cmd = f'echo "{ip}     {hostname}" | sudo tee -a /etc/hosts'
p = os.system('echo %s|sudo -S %s' % (ssh_password, cmd))

logging.info(f'Script complete.')