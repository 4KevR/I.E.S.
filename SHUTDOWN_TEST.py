import paramiko
import time

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  
ssh_client.connect(hostname="192.168.1.26", username="PHOTOVOLTAIK", password="clientTA52")
channel = ssh_client.invoke_shell()
time.sleep(1)
channel.send("sudo /sbin/shutdown -r now\n")
time.sleep(0.5)
channel.send("clientTA52\n")
time.sleep(1)
print(channel.recv(9999).decode("utf-8"))
channel.close()
ssh_client.close()
print("SSH-Verbindung geschlossen")