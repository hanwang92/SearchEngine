import boto.ec2
import time
import os
import subprocess
import string
from boto.manage.cmdshell import sshclient_from_instance

## Start
print '\nStart deployment'
time.sleep(3)

## Setup/start instance
print 'Starting instance...'
time.sleep(3)

region_name = "us-east-1"
kw_params = {"aws_access_key_id":"**********************", "aws_secret_access_key":"*************************"}
conn = boto.ec2.connect_to_region(region_name, **kw_params)
reservation = conn.run_instances("ami-88aa1ce0", key_name="kp1", instance_type='t1.micro', placement="us-east-1a", subnet_id="subnet-edfbfcb4", security_group_ids=["sg-ec03a48a"], dry_run=False)

print 'Starting instance complete!'
time.sleep(3)

## Wait for instance in "running" state and get ip address
print 'Getting instance ip...'
time.sleep(3)

instance = reservation.instances[0]
while instance.update() != "running":
    time.sleep(5)
ipaddr = instance.ip_address
ipaddr = str(ipaddr)
new_str = string.replace(ipaddr, '.', '-')
f = open('upload/ipaddress.txt', 'w')
f.write(new_str)
f.close()

print 'Getting instance ip complete!'
time.sleep(3)

## Upload files using "scp"
print 'Uploading files...\n'
time.sleep(90)

hostaddr = 'ubuntu@' + ipaddr
cmd = 'scp -oStrictHostKeyChecking=no -ri kp1.pem upload/* ' + hostaddr + ':~/'
p = subprocess.Popen(cmd, shell=True)
p.wait()

print '\nUploading files complete!'
time.sleep(3)

## Run deploy script on server 
print 'Running script on server...'
time.sleep(3)

ssh_client = sshclient_from_instance(instance, 'kp1.pem', user_name='ubuntu')
status, stdout, stderr = ssh_client.run('python server_deploy.py')

print 'Running script on server complete!'
time.sleep(3)

print '\nDeployment complete!\n'
time.sleep(3)
print 'IP: ' + ipaddr
dns = 'http://ec2-' + new_str + '.compute-1.amazonaws.com:8080/'
print 'DNS: ' + dns

## End




