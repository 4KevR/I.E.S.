#Das ist das Programm für das Photovoltaik Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys
import RPi.GPIO as GPIO
from itertools import islice

#Analog-Digital Wandler
import board
import busio
import adafruit_ads1x15.ads1115 as ads
from adafruit_ads1x15.analog_in import AnalogIn
i2c = busio.I2C(board.SCL, board.SDA)

#Solarplatten Sensor (4-Kanal)
temp = ads.ADS1115(i2c)
temp.gain = 2/3
chantemp = AnalogIn(temp, ads.P0)

#GPIO-Pins
GPIO.setmode(GPIO.BCM)

#Netzwerk
HOST = '192.168.1.25'
PORT = 55555

#Barriere zum Synchronisieren der Threads
Barriere = th.Barrier(2)

#gibt an, wie viele der Requests in der Datei schon ausgeführt wurden 
textCount = 0

#lege Log-Datei an
with open("/home/PHOTOVOLTAIK/ies/log.txt", "w") as filelog:
    filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))

#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.output = ["0","0","0","0","0",""]
        self.input = ""
        self.energystate = []
        self.openrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[18,26,0]
            }
        
    def setCloseServer(self):
        self.__closeServer = 1
    
    def getCloseServer(self):
        return self.__closeServer
    
    def getVerbrauch(self):
        return sum([entry[0] for key, entry in self.__verbraucher.items() if entry[2] == 1])+sum([entry[0] for key, entry in self.energystate[0].items()])
    
    def getPin(self, device):
        return self.__verbraucher[device][1]
    
    def getState(self, device):
        return self.__verbraucher[device][2]
    
    def invertState(self, device):
        self.__verbraucher[device][2] = (self.__verbraucher[device][2]+1)%2

#Funktionen des Programms
def log(text, bez):
    maxtext = 45 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text)
    with open("/home/PHOTOVOLTAIK/ies/log.txt", "a") as filelogw:
        filelogw.write(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text+"\n")

def connect_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'Verbindungstest Haus Photovoltaik')
        data = s.recv(1024).decode("utf-8")
        log("Antwort erhalten: "+ data,t.getName())
        while not dHandle.getCloseServer():
            log("Warte auf Erhalten von Energiedaten",t.getName())
            Barriere.wait()
            s.sendall(bytes(",".join(dHandle.output), "utf-8"))
            dHandle.output = ""
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
    dHandle.energystate = [{partvalue.split(" ")[0]:partvalue.split(" ")[1] for partvalue in value.split("  ")} for value in dHandle.input[0].split("&&")]
    log(dHandle.energystate, "handleData")
    if len(dHandle.input) > 1:
        for reply in dHandle.input[1:]:
            if reply == "request accepted":
                dHandle.invertState(dHandle.openrequests[0][1])
                GPIO.output(dHandle.getPin(dHandle.openrequests[0][1]), dHandle.getState(dHandle.openrequests[0][1]))
                with open(dHandle.openrequest[0][0]+".txt", "w") as requestWrite:
                    requestWrite.write("accepted")
                del dHandle.openrequests[0]
            elif reply == "request denied":
                with open(dHandle.openrequest[0][0]+".txt", "w") as requestWrite:
                    requestWrite.write("denied")
                del dHandle.openrequests[0]
    
            
######################################################################### 
#Programm
log("Haus Photovoltaik aktiv", "Main")

#initiiere Klasse
dHandle = DataHandle()

#starte Verbindung zum Server als Thread
if not "noNetwork" in sys.argv:
    t = th.Thread(target=connect_server)
    t.start()


#Main
while not dHandle.getCloseServer():
    #Requestdatei lesen
    with open("/home/PHOTOVOLTAIK/ies/request.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/home/PHOTOVOLTAIK/ies/request.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            while dHandle.output[5] == "":
                pass
            if line.strip() != "" and not dHandle.getCloseServer():
                dHandle.output[5] = line.strip().split(" ")[1]
                dHandle.openrequests.append(line.strip().split(" "))
                textCount += 1
    
    #Sensordaten hinzufügen
    #Spannung Solarplatten ermitteln:
    log(str(chantemp.value), "Main")
    log(str(chantemp.voltage), "Main")
    
    averageSol = str(int(chantemp.value*1))
    
    if dHandle.input != "":
        dHandle.output[1] = averageSol
        dHandle.output[2] = dHandle.getVerbrauch()
    
    Barriere.wait()
    
log("Beendet", "Main")