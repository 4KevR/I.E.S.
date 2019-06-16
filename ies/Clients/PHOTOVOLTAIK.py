#Das ist das Programm für das Photovoltaik Haus
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

sys.path.append("/home/PHOTOVOLTAIK/.local/lib/python3.5/site-packages")

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
maxProducedEnergy = 0

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(20, GPIO.OUT)
GPIO.output(26, GPIO.LOW)
GPIO.output(20, GPIO.HIGH)

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
        self.output = ["0","0","0","0","0","none"]
        self.input = ""
        self.energystate = 0
        self.openrequests = []
        self.openexternalrequests = []
        self.__closeServer = 0
        self.__verbraucher = {
            "Lampe":[1000,26,0],
            "Auto":[18000,20,1]
            }
        
    def setCloseServer(self):
        self.__closeServer = 1
    
    def getCloseServer(self):
        return self.__closeServer
    
    def getVerbrauch(self):
        log(str(self.energystate), "getVerbrauch")
        ret = sum([entry[0] for key, entry in self.__verbraucher.items() if (entry[2] == 1 and key != "Auto") or (entry[2] == 0 and key == "Auto")])
        #try:
            #ret += self.energystate
        #except TypeError:
            #ret += 0
        return str(ret) 
    
    def getPin(self, device):
        return self.__verbraucher[device][1]
    
    def getState(self, device):
        return self.__verbraucher[device][2]
    
    def invertState(self, device):
        self.__verbraucher[device][2] = (self.__verbraucher[device][2]+1)%2
        GPIO.output(self.__verbraucher[device][1], self.__verbraucher[device][2])
        
class LED(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        # LED strip configuration:
        self.LED_COUNT      = 134     # Number of LED pixels.
        self.LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
        #self.LED_PIN       = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        self.LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
        self.LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        self.LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
        
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()
        
    def run(self):
        log("starting led", "LED")
        state_alloff = 1
        farben = [Color(109, 239, 0), Color(0, 0, 255), Color(0, 255, 0), Color(255, 0, 0), Color(255, 255, 255)]
        colours = [Color(0,0,0), Color(0,0,0,), Color(0,0,0), Color(0,0,0)]
        
        while not dHandle.getCloseServer():
            try:
                copyOfState = dHandle.energystate.copy()
            except AttributeError:
                copyOfState = ""
            if "{" in str(copyOfState):
                #Dictionary gibt an, dass Energie bekommen wird
                completeVerbrauch = 0
                durchlauf = 0
                maxinlist = [0, 0]
                for key,value in copyOfState.items():
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
                    for i in range(0, self.strip.numPixels(), 8):
                        self.strip.setPixelColor(i+z, colours[0])
                        self.strip.setPixelColor(i+z+1, colours[1])
                        self.strip.setPixelColor(i+z+2, colours[2])
                        self.strip.setPixelColor(i+z+3, colours[3])
                    self.strip.show()
                    if int(completeVerbrauch) != 0:
                        time.sleep((userData.maxLED+userData.minLED)-(userData.maxLED+userData.minLED*((float(completeVerbrauch)/22000)**0.75)))
                        #log(str((userData.maxLED+userData.minLED)-(userData.maxLED+userData.minLED*((float(completeVerbrauch)/22000)**0.75))), "runLED")
                    else:
                        break
                    for i in range(0, self.strip.numPixels(), 2):
                        self.strip.setPixelColor(i+z, 0)
                        self.strip.setPixelColor(i+z+1, 0)
                        self.strip.setPixelColor(i+z+2, 0)
                        self.strip.setPixelColor(i+z+3, 0)
                    state_alloff = 1
            elif int(dHandle.output[1]) > userData.beginShowEnergy:
                #sonst ist der Wert ein Integer und das bedeutet, dass Energie abgegeben wird
                for q in range(8):
                    for i in range(0, self.strip.numPixels(), 8):
                        self.strip.setPixelColor(i+q, Color(109, 255, 0))
                        self.strip.setPixelColor(i+q+1, Color(109, 239, 0))
                        self.strip.setPixelColor(i+q+2, Color(109, 239, 0))
                        self.strip.setPixelColor(i+q+3, Color(109, 239, 0))
                    self.strip.show()
                    if int(dHandle.output[1]) != 0:
                        time.sleep((userData.maxLED+userData.minLED)-(userData.minLED*((float(dHandle.output[1])/float(dHandle.output[4]))**0.75)))
                        #log(str((userData.maxLED+userData.minLED)-(userData.minLED*((float(dHandle.output[1])/float(dHandle.output[4]))**0.75))), "runLED")
                    else:
                        break
                    for i in range(0, self.strip.numPixels(), 2):
                        self.strip.setPixelColor(i+q, 0)
                        self.strip.setPixelColor(i+q+1, 0)
                        self.strip.setPixelColor(i+q+2, 0)
                        self.strip.setPixelColor(i+q+3, 0)
                    state_alloff = 1
            elif state_alloff == 1:
                for i in range(0, self.strip.numPixels()):
                    self.strip.setPixelColor(i, 0)
                self.strip.show()
                state_alloff = 0
        for i in range(0, self.strip.numPixels()):
            self.strip.setPixelColor(i, 0)
        self.strip.show()

class UserData():
    def __init__(self):
        #Normalisierungen aus Datei einlesen
        with open("/home/PHOTOVOLTAIK/ies/input.txt", "r") as getInput:
            data = getInput.readlines()
            dHandle.output[4] = data[3].strip()
            self.maxWert = int(data[6].strip())
            self.beginShowEnergy = int(data[9].strip())
            self.maxLED = float(data[13].strip())
            self.minLED = float(data[16].strip())
            self.normFaktor = int(chantemp.value-30)

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
        s.setblocking(2)
        s.sendall(b'Verbindungstest Haus Photovoltaik')
        data = s.recv(1024).decode("utf-8")
        log("Antwort erhalten: "+ data,t.getName())
        while not dHandle.getCloseServer():
            log("Warte auf Erhalten von Energiedaten",t.getName())
            Barriere.wait()
            s.sendall(bytes(",".join(dHandle.output), "utf-8"))
            dHandle.output[5] = "none"
            dHandle.input = s.recv(1024).decode("utf-8")
            log("Input: "+dHandle.input, t.getName())
            if dHandle.input == "close":
                dHandle.setCloseServer()
                log("Schließe Verbindung zum Brain",t.getName())
            else:
                handleData()
        Barriere.wait()
        
def handleData():
    dHandle.input = dHandle.input.split("||")
    if dHandle.input[0].strip() == "turnoff":
        if dHandle.getState("Auto") == 0:
            dHandle.invertState("Auto")
        if dHandle.getState("Lampe") == 1:
            dHandle.invertState("Lampe")
    elif dHandle.input[0].strip() != "none":
        if len(dHandle.input[0].split("  ")[0].split(" ")) > 1:
            dHandle.energystate = {int(partvalue.split(" ")[0]):int(partvalue.split(" ")[1]) for partvalue in dHandle.input[0].split("  ") if partvalue != "" and partvalue != "0"}
        else:
            try:
                dHandle.energystate = int(dHandle.input[0].strip())
            except ValueError:
                sys.close()
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
                if dHandle.openrequests[0][1] == "Auto":
                    autooff = th.Thread(target=auto_off)
                    autooff.start()
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
                        if request.split(" ")[1] == "Auto":
                            autooff = th.Thread(target=auto_off)
                            autooff.start()
                    else:
                        dHandle.output[5] = request.split(" ")[1]+" declined"
                        removeItem.append(request)
                command = "rm '"+path+"'"
                os.system(command)
        for item in removeItem:
            dHandle.openexternalrequests.remove(item)
                        

def auto_off():
    time.sleep(10)
    if dHandle.getState("Auto") == 0:
        dHandle.invertState("Auto")
            
######################################################################### 
#Programm
log("Haus Photovoltaik aktiv", "Main")

#initiiere Klasse
dHandle = DataHandle()

#Nutzerdaten
userData = UserData()

#starte Verbindung zum Server als Thread
if not "noNetwork" in sys.argv:
    t = th.Thread(target=connect_server)
    t.start()
    
led = LED()
led.start()


#Main
while not dHandle.getCloseServer():
    #Requestdatei lesen
    with open("/var/www/html/input/request.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/var/www/html/input/request.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            if dHandle.output[5] == "none" and line.strip != "" and not dHandle.getCloseServer():
                try:
                    if (dHandle.getState(line.strip().split(" ")[1]) == 0 and line.strip().split(" ")[1] == "Lampe") or (line.strip().split(" ")[1] == "Auto" and dHandle.getState(line.strip().split(" ")[1]) == 1):
                        dHandle.output[5] = line.strip().split(" ")[1]
                    else:
                        dHandle.output[5] = line.strip().split(" ")[1]+" off"
                    dHandle.openrequests.append(line.strip().split(" "))
                    log(str(dHandle.openrequests[-1]), "Main")
                    log("Request zu vorhandenen Requests hinzugefügt", "Main")
                except IndexError:
                    pass
            textCount += 1
    
    #Sensordaten hinzufügen
    #Spannung Solarplatten ermitteln:
    log(str(chantemp.value), "Main")
    log(str(chantemp.voltage), "Main")
    
    averageSol = int(int(dHandle.output[4])*((chantemp.value-userData.normFaktor)/(userData.maxWert-userData.normFaktor)))
    if averageSol < 0:
        averageSol = 0
    
    if averageSol > int(dHandle.output[4]):
        dHandle.output[1] = dHandle.output[4]
    else:
        dHandle.output[1] = str(averageSol)
    dHandle.output[2] = dHandle.getVerbrauch()
    if int(dHandle.output[1]) > maxProducedEnergy:
        maxProducedEnergy = int(dHandle.output[1])
        dHandle.output[3] = str(maxProducedEnergy)
    dHandle.output[0] = str(int(((0.15*int(dHandle.output[4]))+(0.85*int(dHandle.output[3])))/200*((((int(dHandle.output[1])-int(dHandle.output[2]))**2)/100)**0.5)*((int(dHandle.output[1])-int(dHandle.output[2]))/1080000)))
    
    Barriere.wait()
    
log("Beendet", "Main")