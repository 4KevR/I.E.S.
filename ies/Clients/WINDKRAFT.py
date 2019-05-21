#Das ist das Programm für das Windkraft Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys
import RPi.GPIO as GPIO

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(4,GPIO.IN)

#Netzwerk
HOST = '192.168.1.25'
PORT = 55555

#Barriere zum Synchronisieren der Threads
Barriere = th.Barrier(2)

#lege Log-Datei an
with open("/home/WINDKRAFT/ies/log.txt", "w") as filelog:
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
        energy.end = 0
        
    def getCloseServer(self):
        return self.__closeServer

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
        Barriere.wait()
            
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
    #Sensordaten hinzufügen
    dHandle.output[1] = str(energy.speed)
    
    Barriere.wait()
log("Beendet", "Main")