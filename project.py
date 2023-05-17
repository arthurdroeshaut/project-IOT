import RPi.GPIO as GPIO
import time
import datetime
import threading
import busio
import digitalio
import board
import adafruit_pcd8544
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)  # geel
GPIO.setup(27, GPIO.OUT)  # zwart
GPIO.setup(25, GPIO.OUT)  # groen
GPIO.setup(5, GPIO.OUT)  # oranje
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.IN)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(16, GPIO.IN)
GPIO.setup(17, GPIO.LOW)
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)

global is_triggered
global trap_status
global alarm_count
global relay_light

def sensor():
    global is_triggered
    global alarm_count
    global relay_light
    alarm_count = 0
    is_triggered = False
    relay_light = False

    while True:
        global trap_status
        GPIO.output(17, 1)
        time.sleep(0.0001)
        GPIO.output(17, 0)

        while GPIO.input(18) == 0:
            pass
        signal_high = time.time()

        while GPIO.input(18) == 1:
            pass
        signal_low = time.time()

        time_passed = signal_low - signal_high
        distance_sensor = round(time_passed * 17000)
        print("Distance: ", distance_sensor, " cm")

        if distance_sensor <= 6 and not is_triggered:
            # If the distance is shorter than 6cm and trap is not triggered, activate the trap
            is_triggered = True
            relay_light = True
            GPIO.output(26, 0)  # Turn on relay light
            print("Mouse detected!")
            trap_status = "Triggered"
            alarm_count += 1

        elif distance_sensor > 10:
            # If the distance is greater than 10cm, reset the trap
            is_triggered = False
            relay_light = False
            GPIO.output(26, 1)  # Turn off relay light
            trap_status = "Armed"


        time.sleep(0.1)


def lcd():
    global trap_status
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    dc = digitalio.DigitalInOut(board.D23)  # data/command
    cs1 = digitalio.DigitalInOut(board.CE1)  # chip select CE1 for display
    reset = digitalio.DigitalInOut(board.D24)  # reset
    display = adafruit_pcd8544.PCD8544(spi, dc, cs1, reset, baudrate=1000000)
    display.bias = 4
    display.contrast = 60
    display.invert = True

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
        display.image(image)
        display.show()



def motordraai():
    global is_triggered
    global alarm_count
    global relay_light

    while True:
        if is_triggered:
            control_pins = [22, 27, 5, 25]
            for pin in control_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            full_rotation_seq = [
                [1, 0, 0, 0],
                [1, 1, 0, 0],
                [0, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
                [1, 0, 0, 1]
            ]

            num_steps = len(full_rotation_seq)

            # Perform a full rotation of the motor
            for _ in range(num_steps):
                for step in range(8):
                    for pin in range(4):
                        GPIO.output(control_pins[pin], full_rotation_seq[step][pin])
                    time.sleep(0.001)

            # Reset the trigger flag and turn off relay light after a full rotation
            is_triggered = False
            relay_light = False
            GPIO.output(26, GPIO.LOW)  # Turn off relay light

        time.sleep(0.2)



def resetknop():
    global is_triggered
    global alarm_count
    global relay_light
    while True:
        button_state = GPIO.input(12)
        if button_state == GPIO.LOW:
            # Button is pressed
            is_triggered = False  # Set trigger flag to False
            alarm_count = 0  # Reset the count to zero
            relay_light = False #turn off the relay light.
            GPIO.output(26, GPIO.LOW)  # Turn off relay light
            control_pins = [22, 27, 5, 25]
            for pin in control_pins:
                GPIO.output(pin, GPIO.HIGH)  # Stop motor rotation
            time.sleep(0.2)  # Add a small delay to avoid button bounce
        else:
            time.sleep(0.2)  # Add a small delay to avoid unnecessary CPU usage


def triggerknop():
    global is_triggered
    global alarm_count
    global relay_state

    while True:
        button_state = GPIO.input(16)

        if button_state == GPIO.LOW:
            # Button is pressed
            if not is_triggered:
                alarm_count += 1  # Increment the count
                is_triggered = True  # Set trigger flag to True
                GPIO.output(26, GPIO.HIGH)  # Turn on relay light
                relay_state = True  # Update relay state variable
                time.sleep(5)  # Delay for 5 seconds (adjust the duration as needed)
                is_triggered = False  # Reset trigger flag
                GPIO.output(26, GPIO.LOW)  # Turn off relay light

        time.sleep(0.2)  # Add a small delay to avoid excessive checking of button state




thread1 = threading.Thread(target=sensor)
thread2 = threading.Thread(target=lcd)
thread3 = threading.Thread(target=resetknop)
thread4 = threading.Thread(target=triggerknop)
thread5 = threading.Thread(target=motordraai)

thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread5.start()
