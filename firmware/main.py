from machine import Pin, TouchPad
from lights import animate, set_brightness, np
from time import sleep

touch = TouchPad(Pin(4))

PI = 3.1415
ANIM_FRAME = 0
TOUCH_THRESHOLD = 250


while True:
    # Read the touchpad
    try:
        touch_value = touch.read()
    except ValueError:
        continue
    # if touch_value < TOUCH_THRESHOLD:
    #     # Write the NeoPixel data
    animate(np, ANIM_FRAME)

    #     set_brightness(np, 0.1)
    # else:
    set_brightness(np, 1 - min(max(touch_value, 0)/300, 1))

    np.write()
    # Sleep for 0.1 seconds
    sleep(0.01)
    ANIM_FRAME += 1
