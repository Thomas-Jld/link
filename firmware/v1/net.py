import machine
import network
import os
import socket
import time

from parse import unquote_plus
from utils import save_config


def connect_to_wifi(config):
    # Check if wifi credentials are in config.json
    if "wifi" in config and "ssid" in config["wifi"] and "password" in config["wifi"] and config["wifi"]["ssid"] != "":
        # If so, connect to the wifi network
        print("Connecting to wifi network...")
        station = network.WLAN(network.STA_IF)
        station.active(True)
        try:
            station.connect(config["wifi"]["ssid"], config["wifi"]["password"])
        except Exception as e:
            print("Error connecting to wifi: {}".format(e))
            config["wifi"]["ssid"] = ""
            config["wifi"]["password"] = ""
            save_config(config)
        # Wait for connection
        start = time.ticks_ms()
        while station.isconnected() == False:
            if time.ticks_ms() - start > 10000:
                print("Connection timed out")
                break
        else:
            print("Connection successful")
            print(station.ifconfig())
            return True
    else:
        print("No wifi credentials found in config.json")

    return False


def create_access_point(config):
    print("Creating access point...")
    wlan_ap = network.WLAN(network.AP_IF)
    wlan_ap.active(True)
    while not wlan_ap.active():
        pass
    print("Access Point active: {}".format(wlan_ap.active()))
    wlan_ap.config(
        essid=config["hotspot"]["ssid"],
        authmode=network.AUTH_WPA_WPA2_PSK,
        password=config["hotspot"]["password"]
    )
    print("Access Point IP address: {}".format(wlan_ap.ifconfig()[0]))


def wait_for_connection():
    print("Waiting for connection...")
    wlan_ap = network.WLAN(network.AP_IF)
    while not wlan_ap.isconnected():
        pass

    print("Connection successful")
    print(wlan_ap.ifconfig())


def check_access_point():
    wlan_ap = network.WLAN(network.AP_IF)
    return wlan_ap.active()


def host_config_server(config):
    if not check_access_point():
        create_access_point(config)
    else:
        print("Access Point already active")

    wait_for_connection()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Check if port is already in use
    try:
        server.bind(("", 80))
        server.listen(5)
    except OSError:
        print("Port already in use")
        machine.reset()

    while True:
        try:
            conn, addr = server.accept()
            print("Got a connection from %s" % str(addr))

            request = conn.recv(1024)
            request = str(request)
            print("Content = %s" % request)

            # If get request to /config and ssid and password in request, set in config
            if "GET /config" in request:
                if "ssid" in request and "password" in request:
                    # Get ssid and password from request
                    ssid = request[request.find("ssid=") + 5 : request.find("&password=")]
                    password = request[request.find("password=") + 9 : request.find(" HTTP/1.1")]
                    print("New wifi ssid: {}".format(ssid))

                    # Set in config
                    config["wifi"]["ssid"] = unquote_plus(ssid)
                    config["wifi"]["password"] = unquote_plus(password)

                    # Save config
                    save_config(config)

                    # Restart
                    machine.reset()
                else:
                    # If only get request, send html
                    with open("config.html", "r") as f:
                        html = f.read()

                    conn.send(html)
                    html = ""
            else:
                conn.send("Invalid request, please visit /config to configure wifi credentials")

            conn.close()

        except Exception as e:
            print("Connection closed: {}".format(e))
            raise e
