import RPi.GPIO as GPIO
import time
import datetime
import threading
import busio
import digitalio
import board
import adafruit_pcd8544
import spidev
import cgitb ; cgitb.enable() 
import requests
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from adafruit_bus_device.spi_device import SPIDevice

#kleuren
# PIN 17 = geel
# PIN 18 = bruin
# PIN 26 = wit
# PIN 16 = paars

#ubeac variabelen
url = "http://arthurdroeshaut.hub.ubeac.io/iotessarthurdroeshaut"
uid = "iotessarthur droeshaut"



GPIO.setmode(GPIO.BCM)

GPIO.setup(22,GPIO.OUT) #geel
GPIO.setup(27,GPIO.OUT) #zwart
GPIO.setup(25,GPIO.OUT) #groen
GPIO.setup(5,GPIO.OUT) #oranje
#to use raspberry pi GPIO numbers
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.IN)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(17, 0)


# global variabelen
global is_triggered
global trap_status
global alarm_count
rotation = [
                [1,0,0,0],
                [1,1,0,0],
                [0,1,0,0],
                [0,1,1,0],
                [0,0,1,0],
                [0,0,1,1],
                [0,0,0,1],
                [1,0,0,1]
                ]


def resetknop():
    global is_triggered

    # Set up GPIO for the button and relay
    button_pin = 12  
    relay_pin = 26  
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(relay_pin, GPIO.OUT)

    while True:
        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW:
            is_triggered = False
            GPIO.output(26,1)  # Turn off the relay
            time.sleep(0.1)

        time.sleep(0.2)  # Add a small delay to debounce the button
    
def triggerknop():
    global is_triggered
    global alarm_count
    global rotation
    
    # Setup the GPIO for the button and relay
    button_pin = 16
    relay_pin = 26 #lampje
    motor_pins = [22, 27, 5, 25] #motor
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(relay_pin, GPIO.OUT)
    for pin in motor_pins:
        GPIO.setup(pin, GPIO.OUT)
    
    while True:
        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW:
            is_triggered = True
            GPIO.output(26,0)  # Turn on the relay
            time.sleep(0.1)
            
            # Rotate the motor
            for _ in range(80):
                for halfstep in range(8):
                    for pin in range(4):
                        GPIO.output(motor_pins[pin], rotation[halfstep][pin])
                    time.sleep(0.001)
            
            time.sleep(1)  # Adjust the delay according to your requirements
        
        time.sleep(0.2)


    
    
def sensor():
    global is_triggered
    global alarm_count
    alarm_count = 0
    is_triggered = True
    while True:
        global trap_status
        GPIO.output(17,1)
        time.sleep(0.0001)
        GPIO.output(17,0)

        while (GPIO.input(18) == 0):
            pass
        signal_high = time.time()

        while (GPIO.input(18) == 1):
            pass
        signal_low = time.time()

        timepassed = signal_low - signal_high

        distance_sensor = round(timepassed * 17000)
        print("Distance: ", distance_sensor," cm")

        #relay bordje
        if distance_sensor <= 6  and is_triggered == False:
            # Als de afstand korter is dan 6cm dan zit er een muis in de val waardoor er op de LCD "Triggered" komt te staan de de muizen counter omhoog gaat
            GPIO.output(26,0)
            print("Mouse detected!")
            trap_status = "Triggered"
            alarm_count += 1
            is_triggered = True

        elif distance_sensor <= 10:
            trap_status = "Armed"

        else:
            #Als de afstand van de sensor weer hoog is wordt de val gereset
            is_triggered = False
            trap_status = "Armed"


        time.sleep(2)


def lcd():
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Initialize display
    dc = digitalio.DigitalInOut(board.D23)  # data/command
    cs1 = digitalio.DigitalInOut(board.CE1)  # chip select CE1 for display
    reset = digitalio.DigitalInOut(board.D24)  # reset
    display = adafruit_pcd8544.PCD8544(spi, dc, cs1, reset, baudrate= 1000000)
    display.bias = 4
    display.contrast = 60
    display.invert = True


#  Clear the display.  Always call show after changing pixels to make the display update visible!
    display.fill(0)
    display.show()
    current_time = datetime.datetime.now()
    while True:
        display.show()

        font = ImageFont.load_default()

        image = Image.new('1', (display.width, display.height))
        draw = ImageDraw.Draw(image)

        draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)

        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        text = "tijd: " + str(current_time)
        # Write some text.
        nummer=4
        draw.text((1,0), text , font=font)
        draw.text((1,8), trap_status , font=font)
        draw.text((1,24), (str(alarm_count)), font=font)
        # draw.text((1,32), (str(nummer)), font=font)
        display.image(image)
        display.show()
        

        #ubeac
        if trap_status == "Triggered":
            trap_ubeac = 100
        else:
            trap_ubeac = 0
                
            
        data = {
            "id": uid,
            "sensors" : [{
                'id': "trap status",
                'data': trap_ubeac
                }, {
                'id': "alarm count",
                'data': alarm_count}]
            }
        r = requests.post(url, verify = False, json=data)
        print("trap status :", trap_status, "\nalarm count", alarm_count)
        time.sleep(1)


def motordraai():
    while True:
        if is_triggered:
            control_pins = [22,27,5,25]
            for pin in control_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 0)
                halfstep_seq = [
                [1,0,0,0],
                [1,1,0,0],
                [0,1,0,0],
                [0,1,1,0],
                [0,0,1,0],
                [0,0,1,1],
                [0,0,0,1],
                [1,0,0,1]
                ]

                for i in range(80):
                    for halfstep in range(8):
                        for pin in range(4):
                            GPIO.output(control_pins[pin], halfstep_seq[halfstep][pin])
                        time.sleep(0.001)
        else:
            # Stop the motor by turning off all control pins
            control_pins = [22,27,5,25]
            for pin in control_pins:
                GPIO.output(pin, 0)



thread1 = threading.Thread(target=sensor)
thread2 = threading.Thread(target=lcd)
thread3 = threading.Thread(target=resetknop)
thread4 = threading.Thread(target=motordraai)
thread5 = threading.Thread(target=triggerknop)


thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread5.start()
