#Das ist das Programm für die Multifunktionalen Buttons am BRAIN
#Programmiert von Kevin Wiesner

#SMD
#Brain ist an und Programm ist aus = ROT - state 0
#Programm gestartet = GRÜN - state 0
#Programm ist gerade am Starten oder startet neu - state 1
#Pis werden ausgeschaltet = ROT blinkt - state 2
#Pis werden neu gestartet = BLAU - state 3

import RPi.GPIO as GPIO
import time
import threading as th
import os

GPIO.setmode(GPIO.BCM)

button1 = 4
button2 = 17
vorher = 0

GPIO.setup(button1,GPIO.IN)
GPIO.setup(button2,GPIO.IN)

#########################################################################
#Klassen des Programms
class SMD(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.state = 0
        self.smdR = 21
        self.smdG = 20
        self.smdB = 16
        self.retry = 0
        GPIO.setup(self.smdR,GPIO.OUT)
        GPIO.setup(self.smdG,GPIO.OUT)
        GPIO.setup(self.smdB,GPIO.OUT)
    
    def light(self, red, green, blue):
        GPIO.output(self.smdR, red)
        GPIO.output(self.smdG, green)
        GPIO.output(self.smdB, blue)
    
    def run(self):  
        while True:
            if self.state == 2:
                while True:
                    self.light(1,0,0)
                    time.sleep(0.2)
                    self.light(0,0,0)
                    time.sleep(0.2)
            elif self.state == 3:
                self.light(0,0,1)
            elif testactive():
                self.light(0,1,0)
                with open("/home/BRAIN/ies/data.txt", "r") as file:
                    text = file.readlines()
                    if len(text) > 0 and text[0] == "0":
                        time.sleep(0.2)
                        self.light(0,0,0)
                        time.sleep(0.2)
                        self.state = 1
                        self.retry += 1
                        if self.retry > 20:
                            os.system("screen -X -S execute kill")
                            self.retry = 0
                            log("Programm wurde aufgrund von eines inaktiven Pis geschlossen")
                    elif self.state == 1:
                        self.state = 0
                        self.retry = 0
            else:
                self.light(1,0,0)
            
#Funktionen des Programms
def log(text):
    maxtext = 30 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S]")), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S]")+tab+text)

def testactive():
    return "python3 /home/BRAIN/ies/BRAIN.py" in " ".join(os.popen("ps aux").readlines())

def write(task):
    if testactive() and lights.state == 0:
        with open("/home/BRAIN/ies/queue.txt", "a") as file:
            file.write(task+"\n")
    else:
        log("Starte zuerst das Programm oder Task wurde schon gestartet...")

#########################################################################
#Programm
lights = SMD()
lights.start()

while True:
    if GPIO.input(button1) == GPIO.HIGH and vorher == 0:
        time.sleep(0.7)
        if GPIO.input(button1) == GPIO.HIGH:
            if testactive():
                log("Schließe das Programm")
                write("close")
            else:
                log("Starte das Programm")
                os.system("screen -dmS execute python3 /home/BRAIN/ies/BRAIN.py")
        else:
            log("Starte das Programm neu")
            write("restart")
        vorher = 1
    elif GPIO.input(button2) == GPIO.HIGH and vorher == 0 and testactive():
        time.sleep(0.7)
        if GPIO.input(button2) == GPIO.HIGH:
            log("Starte die Pis neu")
            write("reboot")
            lights.state = 3
        else:
            log("Schalte die Pis aus")
            write("shutdown")
            lights.state = 2
        vorher = 1
    elif GPIO.input(button1) == GPIO.LOW and GPIO.input(button2) == GPIO.LOW:
        vorher = 0
    time.sleep(0.1)