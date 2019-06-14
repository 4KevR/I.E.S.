#!/usr/bin/env python3
#Das ist das Utility-Programm wenn das Programm nicht funktioniert
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import paramiko
import sys
import os
import time

#Netzwerk
HOST = '192.168.1.25'
CLIENTS = ['192.168.1.26', '192.168.1.27', '192.168.1.28', '192.168.1.29']
USERNAME = ['PHOTOVOLTAIK', 'WINDKRAFT', 'GEOTHERMIE', 'BIOGAS']
PASSWORD = ['clientTA52', 'clientRA54', 'clientRM56', 'clientOG58']
shutdown = ["sudo /sbin/shutdown -r now\n", "sudo /sbin/shutdown -h now\n"]

def SSH(mode):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(0,4):    
        ssh_client.connect(hostname=CLIENTS[i], username=USERNAME[i], password=PASSWORD[i])
        print("SSH-Verbindung mit: "+USERNAME[i]+" gestartet")
        if mode == 0:
            stdin, stdout, stderr = ssh_client.exec_command("rm /home/"+USERNAME[i]+"/ies/"+USERNAME[i]+".py")
            error = stderr.read().decode("utf-8")
            if error == "":
                print("Altes Programm wurde entfernt")
            else:
                print(error)
            stdin, stdout, stderr = ssh_client.exec_command("rm /var/www/html/output/*.req")
            stdin, stdout, stderr = ssh_client.exec_command("rm /var/www/html/input/*.req")
            stdin, stdout, stderr = ssh_client.exec_command("killall screen")
            sftp_client = ssh_client.open_sftp()
            sftp_client.put('/home/BRAIN/ies/Clients/'+USERNAME[i]+'.py','/home/'+USERNAME[i]+'/ies/'+USERNAME[i]+'.py')
            sftp_client.put('/home/BRAIN/ies/Clients/'+'request.txt','/var/www/html/input/request.txt')
            sftp_client.close()
            print("Neues Programm wurde übertragen")
        if mode == 1 or mode == 2:
            channel = ssh_client.invoke_shell()
            channel.send(shutdown[mode-1])
            time.sleep(0.7)
            channel.send(PASSWORD[i]+"\n")
            time.sleep(0.7)
            channel.close()
        if mode == 3:
            channel = ssh_client.invoke_shell()
            channel.send("sudo su\n")
            time.sleep(0.7)
            channel.send(PASSWORD[i]+"\n")
            time.sleep(0.7)
            channel.send("killall screen\n")
            time.sleep(0.7)
            channel.close()
        ssh_client.close()
        print("SSH-Verbindung geschlossen")
        
#Programm
if sys.argv[1] == "newData":
    SSH(0)
elif sys.argv[1] == "reboot":
    SSH(1)
    os.system("screen -dmS reboot python3 /home/BRAIN/ies/BRAIN_RESTART.py reboot")
elif sys.argv[1] == "shutdown":
    SSH(2)
    os.system("screen -dmS shutdown python3 /home/BRAIN/ies/BRAIN_RESTART.py shutdown")
elif sys.argv[1] == "kill":
    SSH(3)
    task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'killall screen'))
    time.sleep(0.7)
    os.system("screen -dmS button python3 /home/BRAIN/ies/BUTTON.py")
elif sys.argv[1] == "start":
    task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -dmS execute python3 /home/BRAIN/ies/BRAIN.py'))
    
print("UTILITY completed")