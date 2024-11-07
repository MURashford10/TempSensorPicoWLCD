import network
import secrets
import time
import onewire
import ds18x20
import socket
from machine import Pin
from gpio_lcd import GpioLcd

# Initialize LED on GPIO 25 (built-in LED for Pico W)
led = Pin("LED", Pin.OUT)

# Initialize GPIO 27 for controlling the external light
light_pin = Pin(27, Pin.OUT)

# Setup OneWire bus on GPIO 28 for temperature sensor
ow = onewire.OneWire(Pin(28))
ds = ds18x20.DS18X20(ow)

# Scan for devices on the bus
devices = ds.scan()
print('Found devices:', devices)  # Debug print

if not devices:
    print('No temperature sensors found!')

# Initialize the LCD on the desired pins
lcd = GpioLcd(rs_pin=Pin(0),
              enable_pin=Pin(1),
              d4_pin=Pin(2),
              d5_pin=Pin(3),
              d6_pin=Pin(4),
              d7_pin=Pin(5),
              num_lines=2, num_columns=16)

# Wi-Fi Connection Setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.SSID, secrets.PASSWORD)

# Wait for connection with retries
max_attempts = 10
attempts = 0
while not wlan.isconnected() and attempts < max_attempts:
    print('Connecting to WiFi...')
    time.sleep(1)
    attempts += 1

if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    led.value(1)  # Turn on LED when connected to Wi-Fi
    lcd.putstr('WiFi Connected')
else:
    print('Failed to connect to WiFi')
    led.value(0)  # Ensure LED is off if connection fails
    lcd.putstr('WiFi Failed')

time.sleep(2)  # Display connection status briefly
lcd.clear()

# HTML template for the main page
html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temperature Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, rgb(74, 144, 226), rgb(144, 19, 254));
            color: rgb(255, 255, 255);
            text-align: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 15px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(8px);
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 20px;
            font-weight: 600;
        }
        #temps {
            font-size: 1.2rem;
            line-height: 1.6;
        }
        .device {
            background: rgba(255, 255, 255, 0.2);
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            transition: background 0.3s ease;
        }
        .device:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        footer {
            margin-top: 20px;
            font-size: 0.9rem;
            color: rgb(221, 221, 221);
        }
        .loader {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: rgb(255, 255, 255);
            animation: spin 1s ease infinite;
            margin-top: 10px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
    <script>
        function fetchTemperatures() {
            fetch('/temps')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('temps').innerHTML = data;
                })
                .catch(error => console.error('Error fetching temperatures:', error));
        }

        // Auto-update temperatures every 5 seconds
        setInterval(fetchTemperatures, 5000);

        // Fetch temperatures on page load
        window.onload = fetchTemperatures;
    </script>
</head>
<body>
    <div class="container">
        <h1>Temperature Monitor</h1>
        <div id="temps">
            <div class="loader"></div>
            <p>Loading temperatures...</p>
        </div>
        <footer>
            Developed By Clayton Gajewsky 2024. All rights reserved.
        </footer>
    </div>
</body>
</html>
"""

def get_temps_html():
    ds.convert_temp()
    time.sleep_ms(750)  # Wait for the conversion to complete

    temps_html = ""
    light_on = False  # Track if light should be on

    for device in devices:
        temp_c = ds.read_temp(device)  # Read temperature in Celsius
        
        if temp_c is not None:  # Check if the temperature is valid
            temp_f = (temp_c * 9 / 5) + 32  # Convert to Fahrenheit
            temps_html += f"""
                <div class="device">
                    <p>Temperature: {temp_c:.2f}°C / {temp_f:.2f}°F</p>
                </div>
            """
            print(f'Device {device} - Temp: {temp_c:.2f}°C / {temp_f:.2f}°F')  # Debug print
            
            # Update the LCD display with the current temperature
            lcd.clear()
            lcd.putstr(f'Temp: {temp_f:.2f}F')  # Show temperature on LCD
            time.sleep(2)  # Delay to allow time for the user to read the display
        else:
            print(f'Device {device} - Failed to read temperature')  # Debug print for failure case

        # Check if temperature exceeds 72°F
        if temp_f >= 72:
            light_on = True  # Set flag to turn on the light
    
    # Update GPIO 27 based on temperature condition
    light_pin.value(1 if light_on else 0)  # Turn on if above 72°F, off otherwise
    
    return temps_html



# Set up a socket and listen for connections
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Listening on', addr)

while True:
    cl, addr = s.accept()
    print('Client connected from', addr)
    
    request = cl.recv(1024).decode('utf-8')
    print('Request:', request)

    if 'GET /temps' in request:
        # Serve the temperature data only
        temps_html = get_temps_html()
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(temps_html)
    else:
        # Serve the main HTML page
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
    
    cl.close()