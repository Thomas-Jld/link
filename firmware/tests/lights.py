from machine import Pin
from neopixel import NeoPixel
from math import sin

np = NeoPixel(Pin(14), 128)

def set_brightness(np: NeoPixel, brightness: float):
    for i in range(np.n):
        np[i] = (int(np[i][0] * brightness), int(np[i][1] * brightness), int(np[i][2] * brightness))
    np.write()

def animate(np: NeoPixel, frame: int):
    for i in range(np.n):
        val = min(max(sin((i + frame) * 2 * PI / np.n) + 0.5, 0),1)
        np[i] = (int(val * 255 * i / np.n), 0, int(val * 255 * (1 - i / np.n)))
