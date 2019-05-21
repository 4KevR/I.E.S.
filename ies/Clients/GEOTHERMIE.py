#Das ist das Programm für das Geothermie Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys

#Analog-Digital Wandler
import board
import busio
import adafruit_ads1x15.ads1115 as ads
from adafruit_ads1x15.analog_in import AnalogIn
i2c = busio.I2C(board.SCL, board.SDA)

#Temperatur Sensor (4-Kanal)
temp = ads.ADS1115(i2c)
temp.gain = 4
chantemp = [AnalogIn(temp, ads.P0), AnalogIn(temp, ads.P1), AnalogIn(temp, ads.P2), AnalogIn(temp, ads.P3)]

#Netzwerk
HOST = '192.168.1.25'
PORT = 55555

#Barriere zum Synchronisieren der Threads
Barriere = th.Barrier(2)

#lege Log-Datei an
with open("/home/GEOTHERMIE/ies/log.txt", "w") as filelog:
    filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))

#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.output = ["0","0","0","0","0",""]
        self.input = ""
        self.__closeServer = 0
        
    def setCloseServer(self):
        self.__closeServer = 1
    
    def getCloseServer(self):
        return self.__closeServer

#Funktionen des Programms
def log(text, bez):
    maxtext = 45 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text)
    with open("/home/GEOTHERMIE/ies/log.txt", "a") as filelogw:
        filelogw.write(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text+"\n")

def connect_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'Verbindungstest Haus Geothermie')
        data = s.recv(1024).decode("utf-8")
        log("Antwort erhalten: "+ data,t.getName())
        while not dHandle.getCloseServer():
            log("Warte auf Erhalten von Energiedaten",t.getName())
            Barriere.wait()
            log(",".join(dHandle.output), t.getName())
            s.sendall(bytes(",".join(dHandle.output), "utf-8"))
            dHandle.input = s.recv(1024).decode("utf-8")
            log(dHandle.input, t.getName())
            if dHandle.input == "close":
                dHandle.setCloseServer()
                log("Schließe Verbindung zum Brain",t.getName())
        Barriere.wait()
            
#########################################################################   
#Programm
log("Haus Geothermie aktiv", "Main")

#initiiere Klasse
dHandle = DataHandle()

#starte Verbindung zum Server als Thread
if not "noNetwork" in sys.argv:
    t = th.Thread(target=connect_server)
    t.start()


#Main
while not dHandle.getCloseServer():
    #Sensordaten hinzufügen
    #Temperatur ermitteln:
    log("Value: "+str([int(chantemp[i].value) for i in range(0,4)]), "Main")
    log("Voltage: "+str([chantemp[i].voltage for i in range(0,4)]), "Main")
    
    averageTemp = str(int(sum([int(chantemp[i].value) for i in range(0,4)])/4*1.749707))
    
    dHandle.output[1] = averageTemp
    
    Barriere.wait()
log("Beendet", "Main")