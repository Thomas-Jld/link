import network

wlan_ap = network.WLAN(network.AP_IF)
wlan_ap.active(True)
wlan_ap.config(essid="ESP32", authmode=network.AUTH_WPA_WPA2_PSK, password="12345678")

print("Access Point IP address: {}".format(wlan_ap.ifconfig()[0]))
