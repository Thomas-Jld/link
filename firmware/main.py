from machine import Pin, TouchPad
from neopixel import NeoPixel
from time import sleep
from math import sin

np = NeoPixel(Pin(14), 128)
touch = TouchPad(Pin(4))

PI = 3.1415
ANIM_FRAME = 0
TOUCH_THRESHOLD = 250

def set_brightness(np: NeoPixel, brightness: float):
    for i in range(np.n):
        np[i] = (int(np[i][0] * brightness), int(np[i][1] * brightness), int(np[i][2] * brightness))
    np.write()

def animate(np: NeoPixel, frame: int):
    for i in range(np.n):
        val = min(max(sin((i + frame) * 2 * PI / np.n) + 0.5, 0),1)
        np[i] = (int(val * 255 * i / np.n), 0, int(val * 255 * (1 - i / np.n)))


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
