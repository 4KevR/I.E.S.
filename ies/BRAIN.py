#!/usr/bin/env python3
#Das ist das Programm für das Brain
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
from itertools import islice
import paramiko
import sys
import os

#Netzwerk
HOST = '192.168.1.25'
CLIENTS = ['192.168.1.26', '192.168.1.27', '192.168.1.28', '192.168.1.29']
USERNAME = ['PHOTOVOLTAIK', 'WINDKRAFT', 'GEOTHERMIE', 'BIOGAS']
PASSWORD = ['clientTA52', 'clientRA54', 'clientRM56', 'clientOG58']
PORT = 55555
wait = 0.4
shutdown = ["sudo /sbin/shutdown -r now\n", "sudo /sbin/shutdown -h now\n"]

#gibt an, wie viele der Requests in der Datei schon ausgeführt wurden 
textCount = 0

#lege Log-Datei an
if not "noLogsave" in sys.argv:
    with open("/home/BRAIN/ies/log.txt", "w") as filelog:
        filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))
    
#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.input = [[0],[0],[0],[0]]
        self.inputRequest = ["","","",""]
        self.output = ["Back","Back","Back","Back"]
        self.storeEnergy = 10
        self.__closeServer = 0
        self.barriercount = 5
        self.Barriere = th.Barrier(self.barriercount)
    
    def setCloseServer(self):
        self.__closeServer += 1
        log("Set Close Server", "Data Handle")
    
    def getCloseServer(self):
        return self.__closeServer

class GetWeather(th.Thread):
    def __init__(self, event):
        th.Thread.__init__(self)
        self.stopped = event
    
    def run(self):
        timeToWait = 0
        while not self.stopped.wait(timeToWait):
            log("Erhalte Wetterdaten", weather.getName())
            timeToWait = 600

#Funktionen des Programms
def log(text, bez):
    maxtext = 45 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text)
    if not "noLogsave" in sys.argv:
        with open("/home/BRAIN/ies/log.txt", "a") as filelogw:
            filelogw.write(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text+"\n")
    
def network_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        log("Brain Server gestartet", server.getName())
        log("Warte auf Verbindungsanfrage der Häuser...", server.getName())
        connected = 0
        while connected != 4:
            s.listen(4)
            conn, addr = s.accept()
            if addr[0] in CLIENTS:
                log("Got connection from: "+ str(addr), server.getName())
                client = th.Thread(target=new_client, args=[conn,addr,connected])
                client.start()
                connected += 1
            else:
                log("Vebindung verweigert: "+str(addr), server.getName())
                conn.close()
        log("Alle Häuser verbunden - Schließe network_server: "+server.getName(), server.getName())
            
def new_client(conn, addr, name):
    try:
        data = conn.recv(1024)
        log(data.decode("utf-8"), str(addr[0]))
        conn.sendall(b'Verbindung erwiedert')
        while not dHandle.getCloseServer() == 2:
            message = conn.recv(1024).decode("utf-8").split(",")
            log("Received", str(addr[0]))
            try:
                dHandle.input[name] = list(map(int,message[0:5]))
                dHandle.inputRequest[name] = message[5]
            except ValueError:
                log("Value Error: recv() got no response", str(addr[0]))
            dHandle.Barriere.wait()
            dHandle.Barriere.wait()
            conn.sendall(bytes(dHandle.output[name], "utf-8"))
        conn.close()
    except socket.error:
        conn.close()
        log("One client broke the connection", str(addr[0]))
        with open("/home/BRAIN/ies/data.txt", "w") as serverdisconnected:
            serverdisconnected.write("0")
        dHandle.setCloseServer()
        while dHandle.getCloseServer() != 2:
            dHandle.Barriere.wait()
    
def network_handle():
    counter = 0
    while not dHandle.getCloseServer() == 2:
        log("Warte auf Dateneingang...", handle.getName())
        
        dHandle.Barriere.wait()
        
        log("Rohinput: "+str(dHandle.input), handle.getName())
        allProduktion = dHandle.input[0][1]+dHandle.input[1][1]+dHandle.input[2][1]+dHandle.input[3][1]
        allVerbrauch = dHandle.input[0][2]+dHandle.input[1][2]+dHandle.input[2][2]+dHandle.input[3][2]
        
        need = {}
        give = {}
        for i in range(4):
            if dHandle.input[i][1]-dHandle.input[i][2] < 0:
                need[i] = dHandle.input[i][2]-dHandle.input[i][1]
            elif dHandle.input[i][1]-dHandle.input[i][2] > 0:
                give[i] = dHandle.input[i][1]-dHandle.input[i][2]
        log("Gezählte Durchläufe: "+str(counter), handle.getName())
        log("Produktion: "+str(allProduktion), handle.getName())
        log("Verbrauch: "+str(allVerbrauch), handle.getName())
        log("Energie benötigt: "+str(need), handle.getName())
        log("Kann Energie geben: "+str(give), handle.getName())
        with open("/home/BRAIN/ies/data.txt", "w") as save:
            save.write("Photovoltaik_Effizienz="+str(dHandle.input[0][0])+"\nPhotovoltaik_Produktion="+str(dHandle.input[0][1])+"\nPhotovoltaik_Verbrauch="+str(dHandle.input[0][2])+"\nPhotovoltaik_BesteProduktion="+str(dHandle.input[0][3])+"\nPhotovoltaik_MaximalmöglicheProduktion="+str(dHandle.input[0][4])+"\n"+
                       "Windkraft_Effizienz="+str(dHandle.input[1][0])+"\nWindkraft_Produktion="+str(dHandle.input[1][1])+"\nWindkraft_Verbrauch="+str(dHandle.input[1][2])+"\nWindkraft_BesteProduktion="+str(dHandle.input[1][3])+"\nWindkraft_MaximalmöglicheProduktion="+str(dHandle.input[1][4])+"\n"+
                       "Geothermie_Effizienz="+str(dHandle.input[2][0])+"\nGeothermie_Produktion="+str(dHandle.input[2][1])+"\nGeothermie_Verbrauch="+str(dHandle.input[2][2])+"\nGeothermie_BesteProduktion="+str(dHandle.input[2][3])+"\nGeothermie_MaximalmöglicheProduktion="+str(dHandle.input[2][4])+"\n"+
                       "Biogas_Effizienz="+str(dHandle.input[3][0])+"\nBiogas_Produktion="+str(dHandle.input[3][1])+"\nBiogas_Verbrauch="+str(dHandle.input[3][2])+"\nBiogas_BesteProduktion="+str(dHandle.input[3][3])+"\nBiogas_MaximalmöglicheProduktion="+str(dHandle.input[3][4]))
        
        for i in range(4):
            if dHandle.input[i][5] != "":
                dHandle.output[i] = "accepted"
            else:
                dHandle.output[i] = ""
        
        if dHandle.getCloseServer():
            print("Close accepted", handle.getName())
            dHandle.output = ["close" for i in range(0,4)]
            log(str(dHandle.output), handle.getName())
            dHandle.setCloseServer()
            with open("/home/BRAIN/ies/data.txt", "w") as deleteData:
                deleteData.write(str(0))
        time.sleep(wait)
        
        dHandle.Barriere.wait()
        
        counter += 1
    
def queue(command):
    if command == "close" or command == "restart" or command == "clean restart" or command == "reboot" or command == "shutdown":
        log("Befehl zum Beenden des Programms", "Main")
        dHandle.setCloseServer()
        with open("/home/BRAIN/ies/queue.txt", "w") as filedelete:
            filedelete.write("")
        with open("/home/BRAIN/ies/savedEnergy.txt", "w") as saveNewEnergy:
            saveNewEnergy.write(str(storedEnergy))
        stopWeather.set()
        if command == "restart" or command == "clean restart":
            if command == "clean restart":
                log("Befehl zum sauberen Neustarten des Programms", "Main")
                with open("/home/BRAIN/ies/savedEnergy.txt", "w") as resetEnergy:
                    resetEnergy.write("0")
            else:
                log("Befehl zum Neustarten des Programms", "Main")
            os.system("python3 /home/BRAIN/ies/BRAIN_RESTART.py restart")
        if command == "reboot":
            SSH(1)
            os.system("screen -dmS reboot python3 /home/BRAIN/ies/BRAIN_RESTART.py reboot")
        if command == "shutdown":
            SSH(2)
            os.system("screen -dmS shutdown python3 /home/BRAIN/ies/BRAIN_RESTART.py shutdown")
        
def SSH(mode):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(0,4):    
        ssh_client.connect(hostname=CLIENTS[i], username=USERNAME[i], password=PASSWORD[i])
        log("SSH-Verbindung mit: "+USERNAME[i]+" gestartet", "Main")
        if mode == 0:
            stdin, stdout, stderr = ssh_client.exec_command("rm /home/"+USERNAME[i]+"/ies/"+USERNAME[i]+".py")
            error = stderr.read().decode("utf-8")
            if error == "":
                log("Altes Programm wurde entfernt", "Main")
            else:
                log(error, "Main")
            sftp_client = ssh_client.open_sftp()
            sftp_client.put('/home/BRAIN/ies/Clients/'+USERNAME[i]+'.py','/home/'+USERNAME[i]+'/ies/'+USERNAME[i]+'.py')
            sftp_client.close()
            log("Neues Programm wurde übertragen", "Main")
            if not "noNetwork" in sys.argv and not "noExecute" in sys.argv:
                stdin, stdout, stderr = ssh_client.exec_command("screen -dmS execute python3 /home/"+USERNAME[i]+"/ies/"+USERNAME[i]+".py")
                error = stderr.read().decode("utf-8")
                if error == "":
                    log("Programm wird ausgeführt", "Main")
                else:
                    log(error, "Main")
        if mode == 1 or mode == 2:
            channel = ssh_client.invoke_shell()
            channel.send(shutdown[mode-1])
            time.sleep(0.7)
            channel.send(PASSWORD[i]+"\n")
            time.sleep(0.7)
            channel.close()
        ssh_client.close()
        log("SSH-Verbindung geschlossen", "Main")

#########################################################################
#Programm
log("Brain aktiv", "Main")

#Definiere dHandle als Variable des Typs DataHandle()
dHandle = DataHandle()

if not "noNetwork" in sys.argv:
    #starte Server als Thread
    server = th.Thread(target=network_server)
    server.start()
    
    #starte Thread zum Behandeln der Netzwerkdaten
    handle = th.Thread(target=network_handle)
    handle.start()

#starte Thread zum Auslesen der Wetterdaten (alle 10 Minuten)
if not "noWeather" in sys.argv:
    stopWeather = th.Event()
    weather = GetWeather(stopWeather)
    weather.start()

#Übertrage Updates auf Clients:
if not "noSSH" in sys.argv:
    SSH(0)

#Main
with open("/home/BRAIN/ies/savedEnergy.txt", "r") as getStoredEnergy:
    #Energie ist in Joule gespeichert
    storedEnergy = float(getStoredEnergy.readlines()[0])
while not dHandle.getCloseServer():
    #Überprüfe, ob sich etwas etwas neues in der Request Datei hinzugekommen ist, um es in die Warteschlange hinzuzufügen
    with open("/home/BRAIN/ies/queue.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/home/BRAIN/ies/queue.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            if line.strip() != "" and not dHandle.getCloseServer():
                newReq = th.Thread(target=queue, args=[line.strip()])
                newReq.start()
                textCount += 1
    storedEnergy += dHandle.storeEnergy*0.05
    time.sleep(0.05)

time.sleep(1)
log("Aktive Threads: "+str(th.active_count()), "Main")
log("Bezeichnung der Threads: "+str(th.enumerate()), "Main")
log("Beendet", "Main")