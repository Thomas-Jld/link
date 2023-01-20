from machine import TouchPad, Pin
from time import sleep

# create a TouchPad object from a Pin
touch = TouchPad(Pin(4))

while True:
    # read the touchpad
    try:
        touch_value = touch.read()
    except ValueError:
        continue
    print(touch_value)
    sleep(0.1)
