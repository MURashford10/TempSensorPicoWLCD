import network
import secrets
import time
import urequests
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.SSID, secrets.PASSWORD)
print(wlan.isconnected())
ip = wlan.ifconfig()[0]
print(f'Connected on {ip}')
