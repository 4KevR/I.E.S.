#Das ist das Programm für das Windkraft Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys
import RPi.GPIO as GPIO
from itertools import islice

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(4,GPIO.IN)
GPIO.setup(26, GPIO.OUT)

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
        self.output = ["0","0","0","0","0","none"]
        self.input = ""
        self.energystate = []
        self.openrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[18,26,0]
            }
        
    def setCloseServer(self):
        self.__closeServer = 1
        energy.end = 0
        
    def getCloseServer(self):
        return self.__closeServer
    
    def getVerbrauch(self):
        return str(sum([entry[0] for key, entry in self.__verbraucher.items() if entry[2] == 1]))
    
    def getPin(self, device):
        return self.__verbraucher[device][1]
    
    def getState(self, device):
        return self.__verbraucher[device][2]
    
    def invertState(self, device):
        self.__verbraucher[device][2] = (self.__verbraucher[device][2]+1)%2

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
            time.sleep(0.2)
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
                GPIO.output(dHandle.getPin(dHandle.openrequests[0][1]), dHandle.getState(dHandle.openrequests[0][1]))
                with open("/home/WINDKRAFT/ies/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("accepted")
                log("success", "handleData")
                del dHandle.openrequests[0]
            elif reply == "request denied":
                with open("/home/WINDKRAFT/ies/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("denied")
                del dHandle.openrequests[0]
            dHandle.output[5] = "none" 
            
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
    with open("/home/WINDKRAFT/ies/request.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/home/WINDKRAFT/ies/request.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            while dHandle.output[5] != "none":
                pass
            if line.strip() != "" and not dHandle.getCloseServer():
                dHandle.output[5] = line.strip().split(" ")[1]
                dHandle.openrequests.append(line.strip().split(" "))
                log("Request zu vorhandenen Requests hinzugefügt", "Main")
                textCount += 1
                
    #Sensordaten hinzufügen
    dHandle.output[1] = str(energy.speed)
    dHandle.output[2] = dHandle.getVerbrauch()
    
    Barriere.wait()
log("Beendet", "Main")