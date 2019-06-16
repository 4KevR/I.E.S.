#Das ist das Programm für das Biogas Haus
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
from neopixel import *
import multiprocessing
import queue
from ast import literal_eval

sys.path.append("/home/BIOGAS/.local/lib/python3.5/site-packages")

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
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

maxProducedEnergy = 0

#lege Log-Datei an
with open("/home/BIOGAS/ies/log.txt", "w") as filelog:
    filelog.write("Log-Datei vom: "+time.strftime("%d.%m.%Y um %H:%M:%S Uhr\n\n"))

#########################################################################
#Klassen des Programms
class DataHandle():
    def __init__(self):
        self.output = ["0","0","0","0","0","none"]
        self.input = ""
        self.energystate = 0
        self.openrequests = []
        self.openexternalrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[1000,26,0],
            "Waschmaschine":[3000,20,0]
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
    def __init__(self, useData):
        th.Thread.__init__(self)
        self.end = 1
        self.energy = 0
        self.__release = 0
        average = th.Thread(target=self.avrg)
        average.start()
        
        self.userData = useData
        
    def avrg(self):
        while self.end:
            time.sleep(0.2)
            self.__release += 1
            if self.__release == 6:
                self.__release = 0
                self.energy = self.energy*userData.releasePer
        
    def run(self):
        while self.end:
            if GPIO.input(21) == GPIO.HIGH:
                self.energy += userData.addEnergy*(int(dHandle.output[4])-self.energy)
                while GPIO.input(21) == GPIO.HIGH:
                    pass
                
class Stepper(th.Thread):
    def __init__(self, useData):
        th.Thread.__init__(self)
        self.__stepper1 = 4
        self.__stepper2 = 25
        self.__stepper3 = 24
        self.__stepper4 = 23
        GPIO.setup(self.__stepper1,GPIO.OUT)
        GPIO.setup(self.__stepper2,GPIO.OUT)
        GPIO.setup(self.__stepper3,GPIO.OUT)
        GPIO.setup(self.__stepper4,GPIO.OUT)
        
        self.userData = useData
        
    def step(self,w1,w2,w3,w4):
        GPIO.output(self.__stepper1,w1)
        GPIO.output(self.__stepper2,w2)
        GPIO.output(self.__stepper3,w3)
        GPIO.output(self.__stepper4,w4)
        time.sleep(0.1**(energy.energy/5000))
            
    def run(self):
        while energy.end:
            if int(energy.energy) > userData.beginShowEnergy:
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
        
def runLED(minLED, maxLED, beginShow, maxWert):
    log("starting led", "runLED")
    # LED strip configuration:
    LED_COUNT      = 134     # Number of LED pixels.
    LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
    #LED_PIN       = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
    LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
    
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    
    farben = [Color(109, 239, 0), Color(0, 0, 255), Color(0, 255, 0), Color(255, 0, 0), Color(255, 255, 255)]
    colours = [Color(0,0,0), Color(0,0,0,), Color(0,0,0), Color(0,0,0)]
    
    state_alloff = 1
    actual = 0
    counter = 0
    with open("/home/BIOGAS/ies/databetween.txt", "r") as between:
        data = between.readlines()
        data[0] = int(data[0])
        data[1] = int(data[1])
        data[2] = int(data[2])
    while not data[0]:
        #log(str(data), "runLED")
        actual = 0
        if counter == 4:
            while actual == 0:
                try:
                    with open("/home/BIOGAS/ies/databetween.txt", "r") as between:
                        prev = between.readlines()
                        #log(str(prev), "runLEDDATA")
                        if len(prev) == 3:
                            data[0] = int(prev[0])
                            data[1] = int(prev[1])
                            try:
                                data[2] = literal_eval(prev[2])
                            except ValueError:
                                data[2] = int(prev[2])
                            actual = 1
                            counter = 0
                except IndexError:
                    #log("failed Data", "runLED")
                    pass
        counter += 1
        if "{" in str(data[2]):
            #Dictionary gibt an, dass Energie bekommen wird
            completeVerbrauch = 0
            durchlauf = 0
            maxinlist = [0, 0]
            #log(str(data[2]), "runLED")
            for key,value in data[2].items():
                completeVerbrauch += value
                if durchlauf == 0:
                    for i in range(4):
                        colours[i] = farben[key]
                else:
                    colours[-durchlauf] = farben[key]
                    if value > maxinlist[1]:
                        maxinlist = [key, value]
                    if durchlauf == 1:
                        colours[-durchlauf-1] = farben[key]
                durchlauf += 1
            
            if durchlauf == 3:
                colours[1] = farben[maxinlist[0]]
                
            for z in range(8, 0, -1):
                for i in range(0, strip.numPixels(), 8):
                    strip.setPixelColor(i+z, colours[0])
                    strip.setPixelColor(i+z+1, colours[1])
                    strip.setPixelColor(i+z+2, colours[2])
                    strip.setPixelColor(i+z+3, colours[3])
                strip.show()
                if int(completeVerbrauch) != 0:
                    time.sleep((maxLED+minLED)-(maxLED+minLED*((float(completeVerbrauch)/22000)**0.75)))
                    #log(str((maxLED+minLED)-(minLED*((float(data[1])/float(maxWert))**0.75))), "runLED")
                else:
                    break
                for i in range(0, strip.numPixels(), 2):
                    strip.setPixelColor(i+z, 0)
                    strip.setPixelColor(i+z+1, 0)
                    strip.setPixelColor(i+z+2, 0)
                    strip.setPixelColor(i+z+3, 0)
            state_alloff = 1
        elif int(data[1]) > beginShow:
            #sonst ist der Wert ein Integer und das bedeutet, dass Energie abgegeben wird
            for z in range(8):
                for i in range(0, strip.numPixels(), 8):
                    strip.setPixelColor(i+z, Color(255, 0, 0))
                    strip.setPixelColor(i+z+1, Color(255, 0, 0))
                    strip.setPixelColor(i+z+2, Color(255, 0, 0))
                    strip.setPixelColor(i+z+3, Color(255, 0, 0))
                strip.show()
                if int(data[1]) != 0:
                    time.sleep((maxLED+minLED)-(maxLED+minLED*((float(data[1])/float(maxWert))**0.75)))
                    #log(str((maxLED+minLED)-(minLED*((float(data[1])/float(maxWert))**0.75))), "runLED")
                else:
                    break
                for i in range(0, strip.numPixels(), 2):
                    strip.setPixelColor(i+z, 0)
                    strip.setPixelColor(i+z+1, 0)
                    strip.setPixelColor(i+z+2, 0)
                    strip.setPixelColor(i+z+3, 0)
                state_alloff = 1
        elif state_alloff == 1:
            for i in range(0, strip.numPixels()):
                strip.setPixelColor(i, 0)
            strip.show()
            state_alloff = 0
    for i in range(0, strip.numPixels()):
        strip.setPixelColor(i, 0)
    strip.show()
    log("exit off LED", "runLED")
            
class UserData():
    def __init__(self):
        #Normalisierungen aus Datei einlesen
        with open("/home/BIOGAS/ies/input.txt", "r") as getInput:
            data = getInput.readlines()
            dHandle.output[4] = data[3].strip()
            self.releasePer = float(data[6].strip())
            self.addEnergy = float(data[9].strip())
            self.beginShowEnergy = int(data[12].strip())
            self.maxLED = float(data[16].strip())
            self.minLED = float(data[19].strip())

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
    if dHandle.input[0].strip() == "turnoff":
        if dHandle.getState("Waschmaschine") == 1:
            dHandle.invertState("Waschmaschine")
        if dHandle.getState("Lampe") == 1:
            dHandle.invertState("Lampe")
    elif dHandle.input[0].strip() != "none":
        if len(dHandle.input[0].split("  ")[0].split(" ")) > 1:
            dHandle.energystate = {int(partvalue.split(" ")[0]):int(partvalue.split(" ")[1]) for partvalue in dHandle.input[0].split("  ") if partvalue != "" and partvalue != "0"}
        else:
            try:
                dHandle.energystate = int(dHandle.input[0].strip())
            except ValueError:
                sys.exit()
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
                    requestWrite.write("requestdeniedenergyproblemusebattery")
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
            
def networking():
    #q = multiprocessing.Manager().Queue()
    #q = multiprocessing.RawArray('i', [dHandle.getCloseServer(), dHandle.output[1], dHandle.energystate])
    with open("/home/BIOGAS/ies/databetween.txt", "w") as between:
        between.write(str(dHandle.getCloseServer())+"\n"+str(dHandle.output[1])+"\n"+str(dHandle.energystate))
    p = multiprocessing.Process(target=runLED, args=(userData.minLED, userData.maxLED,userData.beginShowEnergy,dHandle.output[4],))
    p.start()
    time.sleep(0.5)
    while not dHandle.getCloseServer():
        with open("/home/BIOGAS/ies/databetween.txt", "w") as between:
            between.write(str(dHandle.getCloseServer())+"\n"+str(dHandle.output[1])+"\n"+str(dHandle.energystate))
    #q.put([dHandle.getCloseServer(), dHandle.output[1], dHandle.energystate])
    time.sleep(1)
    p.terminate()
    p.join()
        
#########################################################################    
#Programm
log("Haus Biogas aktiv", "Main")

#initiiere Klassen
dHandle = DataHandle()

#Nutzerdaten
userData = UserData()

network = th.Thread(target=networking)
network.start()

#Energyhandling
energy = Energy(userData)
energy.start()
steppermotor = Stepper(userData)
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
            if dHandle.output[5] == "none" and line.strip() != "" and not dHandle.getCloseServer():
                try:
                    if dHandle.getState(line.strip().split(" ")[1]) == 0:
                        dHandle.output[5] = line.strip().split(" ")[1]
                    else:
                        dHandle.output[5] = line.strip().split(" ")[1]+" off"
                    dHandle.openrequests.append(line.strip().split(" "))
                    log("Request zu vorhandenen Requests hinzugefügt", "Main")
                except IndexError:
                    pass
            textCount += 1
        
    #Sensordaten hinzufügen
    dHandle.output[1] = str(int(energy.energy))
    dHandle.output[2] = dHandle.getVerbrauch()
    if int(dHandle.output[1]) > maxProducedEnergy:
        maxProducedEnergy = int(dHandle.output[1])
        dHandle.output[3] = str(maxProducedEnergy)
    dHandle.output[0] = str(int(((0.15*int(dHandle.output[4]))+(0.85*int(dHandle.output[3])))/200*((((int(dHandle.output[1])-int(dHandle.output[2]))**2)/100)**0.5)*((int(dHandle.output[1])-int(dHandle.output[2]))/135000000)))
    
    Barriere.wait()

log("Beendet", "Main")