from machine import Pin
from neopixel import NeoPixel

np = NeoPixel(Pin(14), 8)

def set_brightness(np: NeoPixel, brightness: float):
    for i in range(np.n):
        np[i] = (int(np[i][0] * brightness), int(np[i][1] * brightness), int(np[i][2] * brightness))
    np.write()

for i in range(8):
    np[i] = (i * 255 // 8, 0, 255 - i * 255 // 8)

set_brightness(np, 0.5)
np.write()
