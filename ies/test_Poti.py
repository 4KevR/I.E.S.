import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 976000
print("Started SPI")

def write_pot(inp):
    msb = inp >> 8
    lsb = inp & 0xFF
    spi.xfer([msb, lsb])

while True:
    #print("minimum")
    #for i in range(0x00, 0xFF, 1):
        #write_pot(i)
        #print(i)
        #time.sleep(0.05)
    #print("maximum")
    #time.sleep(5)
    #for i in range(0xFF, 0x00, -1):
        #write_pot(i)
        #print(i)
        #time.sleep(0.05)
    write_pot(247)
    time.sleep(1)
    write_pot(248)
    time.sleep(1)
    write_pot(249)
    time.sleep(1)
    write_pot(250)
    time.sleep(1)
    write_pot(251)
    time.sleep(1)
    write_pot(252)
    time.sleep(1)
    write_pot(253)
    time.sleep(1)
    write_pot(254)
    time.sleep(1)
    write_pot(255)
    time.sleep(1)