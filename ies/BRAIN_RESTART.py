#Das ist ein Hilfsprogramm zum Neustarten des Hauptprogramms
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import os
import time
import sys

time.sleep(3)
if sys.argv[1] == "restart":
    os.system("screen -dmS execute python3 /home/BRAIN/ies/BRAIN.py")
elif sys.argv[1] == "reboot":
    task=os.popen('echo %s|sudo -S %s'%('serverAI50', '/sbin/shutdown -r now'))
elif sys.argv[1] == "shutdown":
    task=os.popen('echo %s|sudo -S %s'%('serverAI50', '/sbin/shutdown -h now'))