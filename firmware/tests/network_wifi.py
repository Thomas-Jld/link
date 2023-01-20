import network
import time

wlan_sta = network.WLAN(network.STA_IF)
wlan_sta.active(True)
SSID = "Livebox-32B0"
PASSWORD = "bienvenuechezlesjuldo'sbrothers"

wlan_sta.connect(SSID, PASSWORD)

print("Connecting to WiFi...")
while not wlan_sta.isconnected():
    print(".", end="")
    time.sleep(1)

print("Connected to WiFi!")
print("IP address: {}".format(wlan_sta.ifconfig()[0]))
