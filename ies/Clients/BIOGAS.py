#Das ist das Programm für das Biogas Haus
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import socket
import time
import threading as th
import sys
import RPi.GPIO as GPIO

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.IN)

#Netzwerk
HOST = '192.168.1.25'
PORT = 55555

#Barriere zum Synchronisieren der Threads
Barriere = th.Barrier(2)

#lege Log-Datei an
with open("/home/BIOGAS/ies/log.txt", "w") as filelog:
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
                self.energy += 0.003*(40000-self.energy)
                while GPIO.input(21) == GPIO.HIGH:
                    pass
                
class Stepper(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.__stepper1 = 17
        self.__stepper2 = 18
        self.__stepper3 = 27
        self.__stepper4 = 22
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
                self.step(1,1,0,0)
                #self.step(0,1,0,0)
                self.step(0,1,1,0)
                #self.step(0,0,1,0)
                self.step(0,0,1,1)
                #self.step(0,0,0,1)
                self.step(1,0,0,1)
                #self.step(1,0,0,0)
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
        Barriere.wait()
            
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
    #Sensordaten hinzufügen
    dHandle.output[1] = str(int(energy.energy))
    
    Barriere.wait()
log("Beendet", "Main")