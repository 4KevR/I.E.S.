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
import RPi.GPIO as GPIO
from neopixel import *

sys.path.append("/home/PHOTOVOLTAIK/.local/lib/python3.5/site-packages")
task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -dmS light python3 /home/BRAIN/rpi_ws281x/python/examples/strandtest.py'))

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(14, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)
GPIO.output(14, GPIO.LOW)
GPIO.output(15, GPIO.HIGH)

#Netzwerk
HOST = '192.168.1.25'
CLIENTS = ['192.168.1.26', '192.168.1.27', '192.168.1.28', '192.168.1.29']
USERNAME = ['PHOTOVOLTAIK', 'WINDKRAFT', 'GEOTHERMIE', 'BIOGAS']
PASSWORD = ['clientTA52', 'clientRA54', 'clientRM56', 'clientOG58']
PORT = 55555
wait = 0.05
shutdown = ["sudo /sbin/shutdown -r now\n", "sudo /sbin/shutdown -h now\n"]

#gibt an, wie viele der Requests in der Datei schon ausgeführt wurden 
textCount = 0

Barriere = th.Barrier(5)

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
        self.openrequestsBat = []
        self.openrequestsPow = []
        self.output = ["Back","Back","Back","Back"]
        self.storeEnergy = 0
        self.storedEnergy = 0
        self.giveEnergy = 0
        self.givePowerGrid = [0, 0] # [0] steht für den Verriegelungsstatus, [1] steht für die Energie, die aus dem Netz genommen wird
        self.turnoff = 0
        self.maxStoredEnergy = 2000 #in Wh
        self.ssh = 1
        self.__closeServer = 0
        self.give = {}
        self.need = {}
        self.verbraucher = {
            "Lampe":1000,
            "Auto":18000,
            "Herd":7000,
            "Fernseher":800,
            "Waschmaschine":3000
            }
    
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
            
class Pumpe(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.potistate = 0
        self.newPotistate = 0
         
        self.mode = 0
        self.rest = 0
        self.lock = 0
        #Mode 0
        self.kal = [[0, 16334.597, 21690.675, 27101.206, 32075.526, 36249.453, 40580.852, 44377.941, 47724.32, 50757.413, 52581.67, 555091.886, 57463.303, 60106.998],
                    [0, -17396.145, -22730.17, -28279.458, -34049.487, -39350.736, -44282.911, -48635.276, -53303.851, -57313.077, -59107.533, -61527.028, -63841.399, -67900]]
        self.state = 0
        self.started = 0
        
        #Mode 1
        self.activeStepper = 0
        self.restvorher = 0
        self.startPoint = 0
        self.startPointVorher = 0
        
        #time.sleep(0.4)
        
        self.control_pins = [6, 13, 19, 26]
        for pin in self.control_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)
        self.halfstep_seq = [
            [1,0,0,0],
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1],
            [1,0,0,1],
        ]
        for i in range(90):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(self.control_pins[pin],self.halfstep_seq[halfstep][pin])
                time.sleep(0.002)
        for pin in self.control_pins:
            GPIO.output(pin, 0)
    
    def stepper(self):
        self.activeStepper = 1
        if (self.potistate-self.newPotistate) > 0:
            #Poti muss zurückdrehen
            self.control_pins = [26, 19, 13, 6]
            log("Turning back "+str(self.newPotistate), "Pumpe")
        else:
            #Poti muss vordrehen
            self.control_pins = [6, 13, 19, 26]
            log("Poti dreht vorwärts zu "+str(self.newPotistate), "Pumpe")
            
        for i in range(int(168*((abs(self.potistate-self.newPotistate))/12))):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(self.control_pins[pin],self.halfstep_seq[halfstep][pin])
                time.sleep(0.002)
        for pin in self.control_pins:
            GPIO.output(pin, 0)
        self.potistate = self.newPotistate
        self.activeStepper = 0
        
    def run(self):
        while not dHandle.getCloseServer():
            #Pumpensteuerung
            if dHandle.storedEnergy + (dHandle.storeEnergy*0.1) < int(dHandle.maxStoredEnergy)*3600 and dHandle.storedEnergy + (dHandle.storeEnergy*0.1) >= 0: #Speicherkapazität in dHandle.maxStoredEnergy festgelegt
                dHandle.storedEnergy += dHandle.storeEnergy*0.1
            elif dHandle.storedEnergy + (dHandle.storeEnergy*0.1) < 0:
                dHandle.storedEnergy = 0
            else:
                dHandle.storedEnergy = int(dHandle.maxStoredEnergy)*3600
            time.sleep(0.1)
            if self.mode == 0:
                if dHandle.storeEnergy > 0:
                    self.state = 1
                    GPIO.output(15, GPIO.LOW)
                elif dHandle.storeEnergy < 0:
                    self.state = 2
                    GPIO.output(15, GPIO.HIGH)
                else:
                    self.state = 0
                if self.state > 0:
                    if self.lock != 1:
                        for testState in range(13):
                            if (dHandle.storeEnergy >= self.kal[self.state-1][testState] and dHandle.storeEnergy < self.kal[self.state-1][testState+1] and self.state == 1) or (dHandle.storeEnergy <= self.kal[self.state-1][testState] and dHandle.storeEnergy > self.kal[self.state-1][testState+1] and self.state == 2):
                                if self.potistate != testState-1:
                                    self.newPotistate = testState-1
                                    log("Setze auf Level "+str(self.newPotistate), "Pumpe")
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                    if self.potistate >= 0 or (self.lock == 1 and ((self.rest > 0 and self.state == 1) or (self.rest < 0 and self.state == 2))):
                        GPIO.output(14, GPIO.HIGH)
                        #if dHandle.ssh == 0:
                            #LED.setActive = 1
                    else:
                        GPIO.output(14, GPIO.LOW)
                        #if dHandle.ssh == 0:
                            #LED.setActive = 0
                    
                    if (self.started == -1 and self.rest < 0 and self.state == 1) or (self.started == 1 and self.rest > 0 and self.state == 2):
                        self.rest += (dHandle.storeEnergy*0.1) + (self.kal[self.state-1][self.potistate+1]*0.1)
                    else:
                        self.rest += (dHandle.storeEnergy*0.1) - (self.kal[self.state-1][self.potistate+1]*0.1)
                    if (self.rest > 50000 or self.rest < -50000) and self.lock != 1:
                        log("Pumpe locked", "Pumpe")
                        self.lock = 1
                        self.started = self.rest/abs(self.rest)
                        self.newPotistate = self.potistate+1
                        GPIO.output(14, GPIO.LOW)
                        self.stepper()
                    elif self.lock == 1:
                        if (self.started == -1 and self.rest > 0) or (self.started == 1 and self.rest < 0):
                            self.lock = 0
                            self.started = 0
                else:
                    GPIO.output(14, GPIO.LOW)
                    #if dHandle.ssh == 0:
                        #LED.setActive = 0
            elif self.mode == 1:
                if self.rest > 40000 and self.lock != 2:
                    if dHandle.storeEnergy > 0:
                        self.startPoint = 0
                    elif dHandle.storeEnergy < 0:
                        self.startPoint = 1
                    if self.lock == 0:
                        self.startPointVorher = self.startPoint
                    if self.restvorher < self.rest:
                        if self.startPointVorher != self.startPoint:
                            self.lock = 0
                            self.started = 0
                        elif self.activeStepper == 0:
                            self.lock = 1
                            if self.startPoint == 0:
                                self.newPotistate = self.potistate+1
                            else:
                                self.newPotistate = self.potistate-1
                            GPIO.output(14, GPIO.LOW)
                            self.stepper()
                            #log("Setting to Level"+str(self.newPotistate), "Pumpe")
                            #log("Pumpe neu "+str(self.newPotistate), "Pumpe")
                            #log("Pumpe "+str(self.potistate), "Pumpe")
                elif self.rest < -40000 and self.lock != 1:
                    if dHandle.storeEnergy > 0:
                        self.startPoint = 0
                    elif dHandle.storeEnergy < 0:
                        self.startPoint = 1
                    if self.lock == 0:
                        self.startPointVorher = self.startPoint
                    if self.restvorher > self.rest:
                        if self.startPointVorher != self.startPoint:
                            self.lock = 0
                            self.started = 0
                        elif self.activeStepper == 0:
                            self.lock = 2
                            if self.startPoint == 0:
                                self.newPotistate = self.potistate-1
                            else:
                                self.newPotistate = self.potistate+1
                            GPIO.output(14, GPIO.LOW)
                            self.stepper()
                if self.lock == 1:
                    self.restvorher = self.rest
                    if self.rest < 0:
                        self.lock = 0
                elif self.lock == 2:
                    self.restvorher = self.rest
                    if self.rest > 0:
                        self.lock = 0
                if dHandle.storeEnergy == 0:
                    GPIO.output(14, GPIO.LOW)
                    GPIO.output(15, GPIO.HIGH)
                    LED.setActive = 0
                elif dHandle.storeEnergy > 0:
                    #Energiezufuhr
                    if dHandle.storeEnergy < 16334.597 and self.lock == 0:
                        GPIO.output(14, GPIO.LOW)
                        GPIO.output(15, GPIO.LOW)
                        LED.setActive = 0
                        if self.potistate != 0:
                            self.newPotistate = 0
                            if self.activeStepper == 0:
                                GPIO.output(14, GPIO.LOW)
                                self.stepper()
                        self.rest += dHandle.storeEnergy*0.1
                    else:
                        GPIO.output(14, GPIO.HIGH)
                        GPIO.output(15, GPIO.LOW)
                        LED.setActive = 1
                        if (dHandle.storeEnergy >= 16334.597 and dHandle.storeEnergy < 19012.6 and self.lock == 0) or (self.potistate == 0 and self.lock > 0):
                            #log("Level 1", "Pumpe")
                            #log(str(dHandle.storeEnergy), "Pumpe")
                            if self.potistate != 0:
                                self.newPotistate = 0
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(16334.597*0.1)
                        elif (dHandle.storeEnergy >= 19012.6 and dHandle.storeEnergy < 24395.9 and self.lock == 0) or (self.potistate == 1 and self.lock > 0):
                            #log("Level 2", "Pumpe")
                            #log(str(dHandle.storeEnergy), "Pumpe")
                            if self.potistate != 1:
                                self.newPotistate = 1
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(21690.675*0.1)
                        elif (dHandle.storeEnergy >= 24395.9 and dHandle.storeEnergy < 29588.4 and self.lock == 0) or (self.potistate == 2 and self.lock > 0):
                            #log("Level 3", "Pumpe")
                            if self.potistate != 2:
                                self.newPotistate = 2
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(27101.206*0.1)
                        elif (dHandle.storeEnergy >= 29588.4 and dHandle.storeEnergy < 34162.5 and self.lock == 0) or (self.potistate == 3 and self.lock > 0):
                            if self.potistate != 3:
                                self.newPotistate = 3
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(32075.526*0.1)
                        elif (dHandle.storeEnergy >= 34162.5 and dHandle.storeEnergy < 38415.2 and self.lock == 0) or (self.potistate == 4 and self.lock > 0):
                            if self.potistate != 4:
                                self.newPotistate = 4
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(36249.453*0.1)
                        elif (dHandle.storeEnergy >= 38415.2 and dHandle.storeEnergy < 42479.4 and self.lock == 0) or (self.potistate == 5 and self.lock > 0):
                            if self.potistate != 5:
                                self.newPotistate = 5
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(40580.852*0.1)
                        elif (dHandle.storeEnergy >= 42479.4 and dHandle.storeEnergy < 46051.1 and self.lock == 0) or (self.potistate == 6 and self.lock > 0):
                            if self.potistate != 6:
                                self.newPotistate = 6
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(44377.941*0.1)
                        elif (dHandle.storeEnergy >= 46051.1 and dHandle.storeEnergy < 49240.9 and self.lock == 0) or (self.potistate == 7 and self.lock > 0):
                            if self.potistate != 7:
                                self.newPotistate = 7
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(47724.32*0.1)
                        elif (dHandle.storeEnergy >= 49240.9 and dHandle.storeEnergy < 51669.5 and self.lock == 0) or (self.potistate == 8 and self.lock > 0):
                            if self.potistate != 8:
                                self.newPotistate = 8
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(50757.413*0.1)
                        elif (dHandle.storeEnergy >= 51669.5 and dHandle.storeEnergy < 53836.8 and self.lock == 0) or (self.potistate == 9 and self.lock > 0):
                            if self.potistate != 9:
                                self.newPotistate = 9
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(52581.675*0.1)
                        elif (dHandle.storeEnergy >= 53836.8 and dHandle.storeEnergy < 56277.6 and self.lock == 0) or (self.potistate == 10 and self.lock > 0):
                            if self.potistate != 10:
                                self.newPotistate = 10
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(55091.886*0.1)
                        elif (dHandle.storeEnergy >= 56277.6 and dHandle.storeEnergy < 58785.15 and self.lock == 0) or (self.potistate == 11 and self.lock > 0):
                            if self.potistate != 11:
                                self.newPotistate = 11
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(57463.303*0.1)
                        elif (dHandle.storeEnergy >= 58785.15 and dHandle.storeEnergy < 60106.998 and self.lock == 0) or (self.potistate == 12 and self.lock > 0):
                            if self.potistate != 12:
                                self.newPotistate = 12
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)-(60106.998*0.1)
                else:
                    #Energieabfuhr
                    if dHandle.storeEnergy > -17396.145 and self.lock == 0:
                        GPIO.output(14, GPIO.LOW)
                        GPIO.output(15, GPIO.HIGH)
                        LED.setActive = 0
                        if self.potistate != 0:
                            self.newPotistate = 0
                            if self.activeStepper == 0:
                                GPIO.output(14, GPIO.LOW)
                                self.stepper()
                        self.rest += dHandle.storeEnergy*0.1
                    else:
                        GPIO.output(14, GPIO.HIGH)
                        GPIO.output(15, GPIO.HIGH)
                        LED.setActive = 1
                        if (dHandle.storeEnergy <= -17396.145 and dHandle.storeEnergy > -20063.1 and self.lock == 0) or (self.potistate == 0 and self.lock > 0):
                            if self.potistate != 0:
                                self.newPotistate = 0
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(17396.145*0.1)
                        elif (dHandle.storeEnergy <= -20063.1 and dHandle.storeEnergy > -25504.73 and self.lock == 0) or (self.potistate == 1 and self.lock > 0):
                            if self.potistate != 1:
                                self.newPotistate = 1
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(22730.017*0.1)
                        elif (dHandle.storeEnergy <= -25504.73 and dHandle.storeEnergy > -31164.47 and self.lock == 0) or (self.potistate == 2 and self.lock > 0):
                            if self.potistate != 2:
                                self.newPotistate = 2
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(28279.458*0.1)
                        elif (dHandle.storeEnergy <= -31164.47 and dHandle.storeEnergy > -36700.1 and self.lock == 0) or (self.potistate == 3 and self.lock > 0):
                            if self.potistate != 3:
                                self.newPotistate = 3
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(34049.487*0.1)
                        elif (dHandle.storeEnergy <= -36700.1 and dHandle.storeEnergy > -41816.8 and self.lock == 0) or (self.potistate == 4 and self.lock > 0):
                            if self.potistate != 4:
                                self.newPotistate = 4
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(39350.736*0.1)
                        elif (dHandle.storeEnergy <= -41816.8 and dHandle.storeEnergy > -46459.1 and self.lock == 0) or (self.potistate == 5 and self.lock > 0):
                            if self.potistate != 5:
                                self.newPotistate = 5
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(44282.911*0.1)
                        elif (dHandle.storeEnergy <= -46459.1 and dHandle.storeEnergy > -50969.6 and self.lock == 0) or (self.potistate == 6 and self.lock > 0):
                            if self.potistate != 6:
                                self.newPotistate = 6
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(48635.276*0.1)
                        elif (dHandle.storeEnergy <= -50969.6 and dHandle.storeEnergy > -55308.5 and self.lock == 0) or (self.potistate == 7 and self.lock > 0):
                            if self.potistate != 7:
                                self.newPotistate = 7
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(53303.851*0.1)
                        elif (dHandle.storeEnergy <= -55308.5 and dHandle.storeEnergy > -58210.3 and self.lock == 0) or (self.potistate == 8 and self.lock > 0):
                            if self.potistate != 8:
                                self.newPotistate = 8
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(57313.077*0.1)
                        elif (dHandle.storeEnergy <= -58210.3 and dHandle.storeEnergy > -60317.28 and self.lock == 0) or (self.potistate == 9 and self.lock > 0):
                            if self.potistate != 9:
                                self.newPotistate = 9
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(59107.533*0.1)
                        elif (dHandle.storeEnergy <= -60317.28 and dHandle.storeEnergy > -62684.21 and self.lock == 0) or (self.potistate == 10 and self.lock > 0):
                            if self.potistate != 10:
                                self.newPotistate = 10
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(61527.028*0.1)
                        elif (dHandle.storeEnergy <= -62684.21 and dHandle.storeEnergy > -65870.7 and self.lock == 0) or (self.potistate == 11 and self.lock > 0):
                            if self.potistate != 11:
                                self.newPotistate = 11
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(63841.399*0.1)
                        elif (dHandle.storeEnergy <= -65870.7 and dHandle.storeEnergy > -67900 and self.lock == 0) or (self.potistate == 12 and self.lock > 0):
                            if self.potistate != 12:
                                self.newPotistate = 12
                                if self.activeStepper == 0:
                                    GPIO.output(14, GPIO.LOW)
                                    self.stepper()
                            self.rest += (dHandle.storeEnergy*0.1)+(67900*0.1)
        while self.activeStepper == 1:
            pass
        self.control_pins = [26, 19, 13, 6]
        for i in range(int(100+168*((abs(self.potistate))/12))):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(self.control_pins[pin],self.halfstep_seq[halfstep][pin])
                time.sleep(0.002)
        for pin in self.control_pins:
            GPIO.output(pin, 0)
            
class Starting_led(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        # LED strip configuration:
        self.LED_COUNT      = 20      # Number of LED pixels.
        self.LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
        #self.LED_PIN       = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        self.LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
        self.LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        self.LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.active = 1
        self.setSpeed = 0.1
        self.initiate = 0
        self.setActive = 1
        
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()
    
    def run(self):
        while not dHandle.getCloseServer():
            if self.active == 1 and self.initiate == 0:
                for i in range(self.strip.numPixels()):
                    for z in range(9):
                        self.strip.setPixelColor(i-z, Color(int(255-((z/8)*255)),int(255-((z/8)*255)),int(255-((z/8)*255))))
                    self.strip.show()
                    time.sleep(self.setSpeed)
                #log("Showing LED run "+str(self.setSpeed-(pumpe.potistate/12*0.1)), "runLED")
                #self.setSpeed = 0.008
            elif self.active == 1:
                if dHandle.storeEnergy > 0:
                    counting = [i for i in range(256)]
                else:
                    counting = [i for i in range(255, -1, -1)]
                for i in counting:
                    for led in range(self.strip.numPixels()):
                        self.strip.setPixelColor(led, Color(i, i, i))
                    self.strip.show()
                    time.sleep(0.003)
                        
            if (dHandle.ssh == 0 and self.initiate == 0) or self.setActive == 0:
                self.active = 0
                self.initiate = 1
                for i in range(self.strip.numPixels()):
                    self.strip.setPixelColor(i, Color(255, 255, 255))
                    self.strip.show()
                    time.sleep(self.setSpeed)
                #log("Closing ring", "runLED")
            else:
                self.active = 1
                #log("Setting LED to run", "runLED")

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
            Barriere.wait()
            Barriere.wait()
            conn.sendall(bytes(dHandle.output[name], "utf-8"))
        conn.close()
    except socket.error:
        conn.close()
        log("One client broke the connection", str(addr[0]))
        with open("/var/www/html/input/queue.txt", "w") as filedelete:
            filedelete.write("")
        with open("/var/www/html/output/savedEnergy.txt", "w") as saveNewEnergy:
            saveNewEnergy.write(str(dHandle.storedEnergy))
        stopWeather.set()
        dHandle.setCloseServer()
        while dHandle.getCloseServer() != 2:
            Barriere.wait()
    
def network_handle():
    counter = 0
    while not dHandle.getCloseServer() == 2:
        log("Warte auf Dateneingang...", handle.getName())
        
        Barriere.wait()
        
        log("Rohinput: "+str(dHandle.input), handle.getName())
        allProduktion = dHandle.input[0][1]+dHandle.input[1][1]+dHandle.input[2][1]+dHandle.input[3][1]
        allVerbrauch = dHandle.input[0][2]+dHandle.input[1][2]+dHandle.input[2][2]+dHandle.input[3][2]
        allEffizienz = int((dHandle.input[0][0]+dHandle.input[1][0]+dHandle.input[2][0]+dHandle.input[3][0])/4)
        maxProduktion = dHandle.input[0][4]+dHandle.input[1][4]+dHandle.input[2][4]+dHandle.input[3][4]
        
        dHandle.need = {}
        dHandle.give = {}
        for i in range(4):
            if dHandle.input[i][1]-dHandle.input[i][2] < 0:
                dHandle.need[i] = dHandle.input[i][2]-dHandle.input[i][1]
            elif dHandle.input[i][1]-dHandle.input[i][2] > 0:
                dHandle.give[i] = dHandle.input[i][1]-dHandle.input[i][2]
        log("Gezählte Durchläufe: "+str(counter), handle.getName())
        log("Produktion: "+str(allProduktion), handle.getName())
        log("Verbrauch: "+str(allVerbrauch), handle.getName())
        log("Energie benötigt: "+str(dHandle.need), handle.getName())
        log("Kann Energie geben: "+str(dHandle.give), handle.getName())
        with open("/var/www/html/output/data.txt", "w") as save:
            save.write("Photovoltaik_Effizienz="+str(dHandle.input[0][0])+"\nPhotovoltaik_Produktion="+str(dHandle.input[0][1])+"\nPhotovoltaik_Verbrauch="+str(dHandle.input[0][2])+"\nPhotovoltaik_BesteProduktion="+str(dHandle.input[0][3])+"\nPhotovoltaik_MaximalmöglicheProduktion="+str(dHandle.input[0][4])+"\n"+
                       "Windkraft_Effizienz="+str(dHandle.input[1][0])+"\nWindkraft_Produktion="+str(dHandle.input[1][1])+"\nWindkraft_Verbrauch="+str(dHandle.input[1][2])+"\nWindkraft_BesteProduktion="+str(dHandle.input[1][3])+"\nWindkraft_MaximalmöglicheProduktion="+str(dHandle.input[1][4])+"\n"+
                       "Geothermie_Effizienz="+str(dHandle.input[2][0])+"\nGeothermie_Produktion="+str(dHandle.input[2][1])+"\nGeothermie_Verbrauch="+str(dHandle.input[2][2])+"\nGeothermie_BesteProduktion="+str(dHandle.input[2][3])+"\nGeothermie_MaximalmöglicheProduktion="+str(dHandle.input[2][4])+"\n"+
                       "Biogas_Effizienz="+str(dHandle.input[3][0])+"\nBiogas_Produktion="+str(dHandle.input[3][1])+"\nBiogas_Verbrauch="+str(dHandle.input[3][2])+"\nBiogas_BesteProduktion="+str(dHandle.input[3][3])+"\nBiogas_MaximalmöglicheProduktion="+str(dHandle.input[3][4])+"\n"+
                       "BRAIN_Produktion="+str(allProduktion)+"\nBRAIN_Verbrauch="+str(allVerbrauch)+"\nBRAIN_storedEnergy="+str(int(dHandle.storedEnergy))+"\nBRAIN_Effizienz="+str(allEffizienz)+"\nBRAIN_MaximalmöglicheProduktion="+str(maxProduktion)+"\nBRAIN_maxStoredEnergy="+str(dHandle.maxStoredEnergy)+"\nPumpe_Restenergy="+str(pumpe.rest)+"\nPumpe_Status="+str(pumpe.potistate)+"\nPumpe_Lock="+str(pumpe.lock)+"\nPumpe_Started="+str(pumpe.started))
        
        #Management für das Empfangen von Energie
        energyfromBattery = 0
        energyfromGrid = 0
        for i in range(4):
            dHandle.output[i] = ""
            if i in dHandle.need:
                log("Haus "+str(i)+" braucht "+str(dHandle.need[i])+"W an Energie", handle.getName())
                for client,w in dHandle.give.items():
                    if w >= dHandle.need[i]:
                        dHandle.give[client] -= dHandle.need[i]
                        dHandle.output[i] += str(client) + " " + str(dHandle.need[i]) + "  "
                        dHandle.need[i] = 0
                    else:
                        dHandle.need[i] = dHandle.need[i] - w
                        dHandle.output[i] += str(client) + " " + str(w) + "  "
                        dHandle.give[client] = 0
                    if dHandle.need[i] == 0:
                        break
                if dHandle.need[i] > 0:
                    log("Es gibt zu wenig Energie im System", handle.getName())
                    if dHandle.storedEnergy > (allVerbrauch-allProduktion): #Speicher größer als Abgabe
                        energyfromBattery += dHandle.need[i]
                        dHandle.output[i] += "4 " + str(dHandle.need[i]) + " "
                        dHandle.need[i] = 0
                    if dHandle.need[i] > 0:
                        if dHandle.givePowerGrid[0] == 1:
                            energyfromGrid += dHandle.need[i]
                            dHandle.output[i] += "5 " + str(dHandle.need[i]) + " "
                            dHandle.need[i] = 0
                        else:
                            dHandle.turnoff = 1
                            log("Kritischer Energiezustand - schalte alle Verbraucher aus", handle.getName())
        
        dHandle.giveEnergy = energyfromBattery
        dHandle.givePowerGrid[1] = energyfromGrid
                        
        #Management für das Geben von Energie
        for i in range(4):
            if i in dHandle.give:
                if dHandle.input[i][1]-dHandle.input[i][2] != dHandle.give[i]:
                    dHandle.output[i] += str(dHandle.input[i][1]-dHandle.input[i][2]-dHandle.give[i]) + "  "
        log(str(dHandle.output), "Data Handle")
        
        #Management für das Akzenptieren von Requests
        for i in range(4):
            if dHandle.output[i] == "":
                dHandle.output[i] = "none"
            if dHandle.inputRequest[i] != "none":
                if len(dHandle.inputRequest[i].split(" ")) > 1 and "off" not in dHandle.inputRequest[i]:
                    #Batteryrequests
                    if str(i)+" "+dHandle.inputRequest[i].split(" ")[0] in dHandle.openrequestsBat and dHandle.inputRequest[i].split(" ")[1] == "accepted":
                        dHandle.openrequestsBat.remove(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
                    elif str(i)+" "+dHandle.inputRequest[i].split(" ")[0] in dHandle.openrequestsBat and dHandle.inputRequest[i].split(" ")[1] == "declined":
                        dHandle.openrequestsBat.remove(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
                        
                    #Power-Grid Requests
                    if str(i)+" "+dHandle.inputRequest[i].split(" ")[0] in dHandle.openrequestsPow and dHandle.inputRequest[i].split(" ")[1] == "accepted":
                        dHandle.openrequestsPow.remove(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
                        #dHandle.givePowerGrid[0] = 1
                    elif str(i)+" "+dHandle.inputRequest[i].split(" ")[0] in dHandle.openrequestsPow and dHandle.inputRequest[i].split(" ")[1] == "declined":
                        dHandle.openrequestsPow.remove(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
                    
                #Allgemeiene Steuerung
                elif dHandle.verbraucher[dHandle.inputRequest[i].split(" ")[0]] < allProduktion-allVerbrauch or (len(dHandle.inputRequest[i].split(" ")) > 1 and "off" in dHandle.inputRequest[i]):
                    dHandle.output[i] += "||request accepted"
                elif dHandle.storedEnergy > 112.500:
                    dHandle.output[i] += "||request denied - Energy from battery?"
                    dHandle.openrequestsBat.append(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
                else:
                    dHandle.output[i] += "||request denied - Energy from public power grid?"
                    dHandle.openrequestsPow.append(str(i)+" "+dHandle.inputRequest[i].split(" ")[0])
        if dHandle.storedEnergy != int(dHandle.maxStoredEnergy)*3600 or dHandle.giveEnergy > 0:
            dHandle.storeEnergy = sum([w for giver,w in dHandle.give.items()])*0.5-dHandle.giveEnergy
        else:
            dHandle.storeEnergy = 0
        log(str(dHandle.storeEnergy), handle.getName())
        
        if dHandle.turnoff == 1:
            for i in range(4):
                dHandle.output[i] = "turnoff"
            dHandle.turnoff = 0
        
        if dHandle.getCloseServer():
            print("Close accepted", handle.getName())
            dHandle.output = ["close" for i in range(0,4)]
            log(str(dHandle.output), handle.getName())
            dHandle.setCloseServer()
            with open("/var/www/html/output/data.txt", "w") as deleteData:
                deleteData.write(str(0))
        time.sleep(wait)
        
        Barriere.wait()
        counter += 1
    
def queue(command):
    if command == "close" or command == "restart" or command == "clean restart" or command == "reboot" or command == "shutdown":
        log("Befehl zum Beenden des Programms", "Main")
        dHandle.setCloseServer()
        task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -XS light kill'))
        with open("/var/www/html/input/queue.txt", "w") as filedelete:
            filedelete.write("")
        with open("/var/www/html/output/savedEnergy.txt", "w") as saveNewEnergy:
            saveNewEnergy.write(str(dHandle.storedEnergy))
        stopWeather.set()
        if command == "restart" or command == "clean restart":
            if command == "clean restart":
                log("Befehl zum sauberen Neustarten des Programms", "Main")
                with open("/var/www/html/output/savedEnergy.txt", "w") as resetEnergy:
                    resetEnergy.write("0")
            else:
                log("Befehl zum Neustarten des Programms", "Main")
            #os.system("screen -dmS restart python3 /home/BRAIN/ies/BRAIN_RESTART.py restart")
            task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -dmS restart python3 /home/BRAIN/ies/BRAIN_RESTART.py restart'))
        if command == "reboot":
            SSH(1)
            #os.system("screen -dmS reboot python3 /home/BRAIN/ies/BRAIN_RESTART.py reboot")
            task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -dmS restart python3 /home/BRAIN/ies/BRAIN_RESTART.py reboot'))
        if command == "shutdown":
            SSH(2)
            #os.system("screen -dmS shutdown python3 /home/BRAIN/ies/BRAIN_RESTART.py shutdown")
            task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -dmS restart python3 /home/BRAIN/ies/BRAIN_RESTART.py shutdown'))
        time.sleep(2)
        
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
            stdin, stdout, stderr = ssh_client.exec_command("rm /var/www/html/output/*.req")
            stdin, stdout, stderr = ssh_client.exec_command("rm /var/www/html/input/*.req")
            sftp_client = ssh_client.open_sftp()
            sftp_client.put('/home/BRAIN/ies/Clients/'+USERNAME[i]+'.py','/home/'+USERNAME[i]+'/ies/'+USERNAME[i]+'.py')
            sftp_client.put('/home/BRAIN/ies/Clients/'+'request.txt','/var/www/html/input/request.txt')
            sftp_client.close()
            log("Neues Programm wurde übertragen", "Main")
            if not "noNetwork" in sys.argv and not "noExecute" in sys.argv:
                channel = ssh_client.invoke_shell()
                channel.send("sudo su\n")
                time.sleep(0.6)
                channel.send(PASSWORD[i]+"\n")
                time.sleep(0.4)
                #channel.send("export LD_PRELOAD='/usr/lib/libtcmalloc_minimal.so.4.3.0'\n")
                #time.sleep(0.3)
                channel.send("killall screen\n")
                time.sleep(0.2)
                # channel.send("rm /home/"+USERNAME[i]+"/screenlog.0\n")
                # time.sleep(0.2)
                # channel.send("touch /home/"+USERNAME[i]+"/screenlog.0\n")
                time.sleep(0.2)
                channel.send("screen -dmS execute python3 /home/"+USERNAME[i]+"/ies/"+USERNAME[i]+".py\n")
                time.sleep(0.2)
                channel.close()
        if mode == 1 or mode == 2:
            channel = ssh_client.invoke_shell()
            channel.send(shutdown[mode-1])
            time.sleep(0.7)
            channel.send(PASSWORD[i]+"\n")
            time.sleep(0.7)
            channel.close()
        ssh_client.close()
        log("SSH-Verbindung geschlossen", "Main")
    dHandle.ssh = 0
        

#########################################################################
#Programm
log("Brain aktiv", "Main")

#Definiere dHandle als Variable des Typs DataHandle()
dHandle = DataHandle()

pumpe = Pumpe()
pumpe.start()

#LED = Starting_led()
#LED.start()

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

with open("/var/www/html/output/savedEnergy.txt", "r") as getStoredEnergy:
    #Energie ist in Joule gespeichert
    dHandle.storedEnergy = float(getStoredEnergy.readlines()[0])

#Übertrage Updates auf Clients:
if not "noSSH" in sys.argv:
    SSH(0)
    

#Main
while not dHandle.getCloseServer():
    #Überprüfe, ob sich etwas etwas neues in der Request Datei hinzugekommen ist, um es in die Warteschlange hinzuzufügen
    with open("/var/www/html/input/queue.txt", "r") as file:
        for line in islice(file, textCount, sum(1 for line in open("/var/www/html/input/queue.txt"))):
            log("Erhaltene Request: "+line.strip(), "Main")
            if line.strip() != "" and not dHandle.getCloseServer():
                newReq = th.Thread(target=queue, args=[line.strip()])
                newReq.start()
                textCount += 1

time.sleep(1)
GPIO.output(14, GPIO.LOW)
GPIO.output(15, GPIO.HIGH)
log("Aktive Threads: "+str(th.active_count()), "Main")
log("Bezeichnung der Threads: "+str(th.enumerate()), "Main")
log("Beendet", "Main")