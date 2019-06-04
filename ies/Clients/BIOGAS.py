#Das ist das Programm für das Biogas Haus
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
GPIO.setup(21,GPIO.IN)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(20, GPIO.OUT)
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
with open("/home/BIOGAS/ies/log.txt", "w") as filelog:
    filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))

#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.output = ["0","0","0","0","30000","none"]
        self.input = ""
        self.energystate = []
        self.openrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[1000,26,0],
            "Waschmaschiene":[3000,20,0]
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
        GPIO.output(dHandle.__verbraucher[device][1], dHandle.__verbrauch[device][2])

class Energy(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.end = 1
        self.energy = 0
        self.__release = 0
        average = th.Thread(target=self.avrg)
        average.start()
        
    def avrg(self):
        while self.end:
            time.sleep(0.2)
            self.__release += 1
            if self.__release == 6:
                self.__release = 0
                self.energy = self.energy*0.92
        
    def run(self):
        while self.end:
            if GPIO.input(21) == GPIO.HIGH:
                self.energy += 0.004*(30000-self.energy)
                while GPIO.input(21) == GPIO.HIGH:
                    pass
                
class Stepper(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.__stepper1 = 22
        self.__stepper2 = 27
        self.__stepper3 = 18
        self.__stepper4 = 17
        GPIO.setup(self.__stepper1,GPIO.OUT)
        GPIO.setup(self.__stepper2,GPIO.OUT)
        GPIO.setup(self.__stepper3,GPIO.OUT)
        GPIO.setup(self.__stepper4,GPIO.OUT)
        
    def step(self,w1,w2,w3,w4):
        GPIO.output(self.__stepper1,w1)
        GPIO.output(self.__stepper2,w2)
        GPIO.output(self.__stepper3,w3)
        GPIO.output(self.__stepper4,w4)
        time.sleep(0.2**(energy.energy/5000))
            
    def run(self):
        while energy.end:
            if int(energy.energy) > 5000:
                self.step(1,0,0,0)
                self.step(1,1,0,0)
                self.step(0,1,0,0)
                self.step(0,1,1,0)
                self.step(0,0,1,0)
                self.step(0,0,1,1)
                self.step(0,0,0,1)
                self.step(1,0,0,1)
            else:
                self.step(0,0,0,0)

#Funktionen des Programms
def log(text, bez):
    maxtext = 45 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text)
    with open("/home/BIOGAS/ies/log.txt", "a") as filelogw:
        filelogw.write(time.strftime("[%d.%m.%Y %H:%M:%S: ")+bez+"]"+tab+text+"\n")

def connect_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'Verbindungstest Haus Biogas')
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
                with open("/var/www/html/output/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("accepted")
                log("success", "handleData")
                del dHandle.openrequests[0]
            elif reply == "request denied":
                with open("/var/www/html/output/"+dHandle.openrequests[0][0]+".req", "w") as requestWrite:
                    requestWrite.write("denied")
                del dHandle.openrequests[0]
            dHandle.output[5] = "none" 
            
#########################################################################    
#Programm
log("Haus Biogas aktiv", "Main")

#initiiere Klassen
dHandle = DataHandle()
energy = Energy()
energy.start()
steppermotor = Stepper()
steppermotor.start()

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
            while dHandle.output[5] != "none":
                pass
            if line.strip() != "" and not dHandle.getCloseServer():
                dHandle.output[5] = line.strip().split(" ")[1]
                dHandle.openrequests.append(line.strip().split(" "))
                log("Request zu vorhandenen Requests hinzugefügt", "Main")
                textCount += 1
                
    #Sensordaten hinzufügen
    dHandle.output[1] = str(int(energy.energy))
    dHandle.output[2] = dHandle.getVerbrauch()
    
    Barriere.wait()
    
log("Beendet", "Main")