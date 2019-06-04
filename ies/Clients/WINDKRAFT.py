#Das ist das Programm für das Windkraft Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys
import RPi.GPIO as GPIO
from itertools import islice
from pathlib import Path
import os

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(4,GPIO.IN)
GPIO.setup(26,GPIO.OUT)
GPIO.setup(20,GPIO.OUT)
GPIO.output(26, GPIO.LOW)
GPIO.output(20, GPIO.LOW)

#Netzwerk
HOST = '192.168.1.25'
PORT = 55555

#Barriere zum Synchronisieren der Threads
Barriere = th.Barrier(2)

#gibt an, wie viele der Requests in der Datei schon ausgeführt wurden 
textCount = 0

#lege Log-Datei an
with open("/home/WINDKRAFT/ies/log.txt", "w") as filelog:
    filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))

#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.output = ["0","0","0","0","10000","none"]
        self.input = ""
        self.energystate = []
        self.openrequests = []
        self.openexternalrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[1000,26,0],
            "Herd":[7000,20,0]
            }
        
    def setCloseServer(self):
        self.__closeServer = 1
        energy.end = 0
        
    def getCloseServer(self):
        return self.__closeServer
    
    def getVerbrauch(self):
        ret = sum([entry[0] for key, entry in self.__verbraucher.items() if entry[2] == 1])
        return str(ret) 
    
    def getPin(self, device):
        return self.__verbraucher[device][1]
    
    def getState(self, device):
        return self.__verbraucher[device][2]
    
    def invertState(self, device):
        self.__verbraucher[device][2] = (self.__verbraucher[device][2]+1)%2
        GPIO.output(dHandle.__verbraucher[device][1], dHandle.__verbraucher[device][2])

class Energy(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.end = 1
        self.__count = 0
        self.speed = 0
        average = th.Thread(target=self.avrg)
        average.start()
        
    def avrg(self):
        while self.end:
            time.sleep(1)
            self.speed = self.__count
            self.__count = 0
            log(str(self.speed), "Energy")
        
    def run(self):
        while self.end:
            if GPIO.input(4) == GPIO.HIGH:
                self.__count += 1
                while GPIO.input(4) == GPIO.HIGH:
                    pass

#Funktionen des Programms
def log(text, bez):
    maxtext = 45 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text)
    with open("/home/WINDKRAFT/ies/log.txt", "a") as filelogw:
        filelogw.write(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text+"\n")

def connect_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'Verbindungstest Haus Windkraft')
        data = s.recv(1024).decode("utf-8")
        log("Antwort erhalten: "+ data,t.getName())
        while not dHandle.getCloseServer():
            log("Warte auf Erhalten von Energiedaten",t.getName())
            Barriere.wait()
            s.sendall(bytes(",".join(dHandle.output), "utf-8"))
            dHandle.output[5] = "none"
            dHandle.input = s.recv(1024).decode("utf-8")
            log(dHandle.input, t.getName())
            if dHandle.input == "close":
                dHandle.setCloseServer()
                log("Schließe Verbindung zum Brain",t.getName())
            else:
                handleData()
        Barriere.wait()
        
def handleData():
    dHandle.input = dHandle.input.split("||")
    if dHandle.input[0].strip() != "none":
        if len(dHandle.input[0].split("  ")[0].split(" ")) > 1:
            dHandle.energystate = {int(partvalue.split(" ")[0]):int(partvalue.split(" ")[1]) for partvalue in dHandle.input[0].split("  ") if partvalue != "" and partvalue != "0"}
        else:
            dHandle.energystate = int(dHandle.input[0].strip())
    else:
        dHandle.energystate = 0
    log(str(dHandle.energystate), "handleData")
    if len(dHandle.input) > 1:
        for reply in dHandle.input[1:]:
            if reply == "request accepted":
                log("request was accepted", "handleData")
                dHandle.invertState(dHandle.openrequests[0][1])
                with open("/var/www/html/output/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("request accepted")
                log("success", "handleData")
            elif reply == "request denied - Energy from battery?":
                with open("/var/www/html/output/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("request denied - Energy from battery?")
                if " ".join(dHandle.openrequests[0]) not in dHandle.openexternalrequests:
                    dHandle.openexternalrequests.append(" ".join(dHandle.openrequests[0]))
            elif reply == "request denied - Energy from public power grid?":
                with open("/var/www/html/output/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("request denied - Energy from public power grid?")
                if " ".join(dHandle.openrequests[0]) not in dHandle.openexternalrequests:
                    dHandle.openexternalrequests.append(" ".join(dHandle.openrequests[0]))
            del dHandle.openrequests[0]
            dHandle.output[5] = "none"
    if len(dHandle.openexternalrequests) > 0 and dHandle.output[5] == "none":
        log("There are open external requests", "handleData")
        log(str(dHandle.openexternalrequests), "handleData")
        removeItem = []
        for request in dHandle.openexternalrequests:
            path = "/var/www/html/input/"+request+".req"
            file = Path(path)
            if file.is_file():
                with open(path, "r") as readRequest:
                    if readRequest.readlines()[0] == "accepted":
                        dHandle.invertState(request.split(" ")[1])
                        dHandle.output[5] = request.split(" ")[1]+" accepted"
                        removeItem.append(request)
                    else:
                        dHandle.output[5] = request.split(" ")[1]+" declined"
                        removeItem.append(request)
                command = "rm '"+path+"'"
                os.system(command)
        for item in removeItem:
            dHandle.openexternalrequests.remove(item)
            
#########################################################################    
#Programm
log("Haus Windkraft aktiv", "Main")

#initiiere Klasse
dHandle = DataHandle()

#initiiere Klasse
energy = Energy()
energy.start()

#starte Verbindung zum Server als Thread
if not "noNetwork" in sys.argv:
    t = th.Thread(target=connect_server)
    t.start()


#Main
while not dHandle.getCloseServer():
    #Requestdatei lesen
    with open("/var/www/html/input/request.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/var/www/html/input/request.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            if dHandle.output[5] == "none" and line.strip() != "" and not dHandle.getCloseServer():
                if dHandle.getState(line.strip().split(" ")[1]) == 0:
                    dHandle.output[5] = line.strip().split(" ")[1]
                else:
                    dHandle.output[5] = line.strip().split(" ")[1]+" off"
                dHandle.openrequests.append(line.strip().split(" "))
                log("Request zu vorhandenen Requests hinzugefügt", "Main")
                textCount += 1
                
    #Sensordaten hinzufügen
    if energy.speed*500 > int(dHandle.output[4]):
        dHandle.output[1] = dHandle.output[4]
    else:    
        dHandle.output[1] = str(energy.speed*500)
    dHandle.output[2] = dHandle.getVerbrauch()
    
    Barriere.wait()
    
log("Beendet", "Main")