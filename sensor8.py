import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button, Buzzer
import threading
from collections import deque
import numpy as np
import csv
import os

# ---------------- GPIO Setup ----------------
pir = DigitalInputDevice(17)
flow_sensor = Button(27, pull_up=True)
flame_sensor = DigitalInputDevice(18)
mq135 = DigitalInputDevice(24)
buzzer = Buzzer(26)

# DHT22 Setup
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# BME280 Setup
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# ---------------- CSV Logging Setup ----------------
csv_file = "/home/gaurav/iotiot-venv/industrial_data.csv"
headers = [
    "timestamp", "motion", "flame", "gas_digital", 
    "flow_rate", "bme_temp", "bme_hum", "bme_pres", 
    "dht_temp", "dht_hum", "label"
]

# Create file and write header if it doesn't exist
if not os.path.isfile(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

# ---------------- DHT Background Thread ----------------
dht_temp, dht_hum = None, None

def read_dht_background():
    global dht_temp, dht_hum
    while True:
        try:
            dht_temp = dht_device.temperature
            dht_hum = dht_device.humidity
        except:
            pass
        time.sleep(3)

threading.Thread(target=read_dht_background, daemon=True).start()

# ---------------- Flow Counter ----------------
pulse_count = 0
def count_pulse():
    global pulse_count
    pulse_count += 1

flow_sensor.when_pressed = count_pulse

# ---------------- Dynamic Threshold Buffers ----------------
WINDOW_SIZE = 30
K_TEMP = 2.0
K_FLOW = 2.0
K_GAS  = 1.5

buffers = {
    "temp": deque(maxlen=WINDOW_SIZE),
    "flow": deque(maxlen=WINDOW_SIZE),
    "gas":  deque(maxlen=WINDOW_SIZE)
}

def dynamic_threshold(data, k):
    if len(data) < 10:
        return None
    return np.mean(data) + k * np.std(data)

# ---------------- System Init ----------------
print("--- Industrial Monitoring & Data Logger ---")
print(f"Logging data to: {csv_file}")
print("PIR stabilizing... Please wait.")
time.sleep(10)
print("System Ready!")

last_time = time.time()

try:
    while True:
        # -------- FAST SENSOR READ --------
        motion_val = int(pir.value)
        flame_val = int(flame_sensor.value)
        gas_val = 0 if  mq135.value else 1   

        # -------- FLOW CALCULATION --------
        current_time = time.time()
        elapsed = current_time - last_time
        flow_rate = (pulse_count / elapsed / 7.5) if elapsed > 0 else 0
        pulse_count = 0
        last_time = current_time

        # -------- BME280 --------
        try:
            b_temp = bme280.temperature
            b_hum = bme280.humidity
            b_pres = bme280.pressure
        except:
            b_temp, b_hum, b_pres = 0, 0, 0

        # -------- UPDATE BUFFERS --------
        buffers["temp"].append(b_temp)
        buffers["flow"].append(flow_rate)
        buffers["gas"].append(gas_val)

        # -------- COMPUTE DYNAMIC THRESHOLDS --------
        temp_th = dynamic_threshold(buffers["temp"], K_TEMP)
        flow_th = dynamic_threshold(buffers["flow"], K_FLOW)
        gas_th  = dynamic_threshold(buffers["gas"], K_GAS)

        # -------- ALERT LOGIC & LABELING --------
        baseline_alerts = []
        if temp_th and b_temp > temp_th: baseline_alerts.append("OVERHEAT")
        if flow_th and flow_rate > flow_th: baseline_alerts.append("WATER LEAK")
        if gas_th and gas_val < gas_th: baseline_alerts.append("GAS LEAK")
        
        # Determine the Label for Machine Learning
        # 0 = Normal, 1 = Anomaly/Alert
        is_alert = 1 if (motion_val or flame_val or gas_val == 1 or baseline_alerts) else 0

        # Control Buzzer
        if is_alert:
            buzzer.on()
        else:
            buzzer.off()

        # -------- SAVE TO CSV --------
        # We only log data if DHT is ready to avoid empty columns in your dataset
        if dht_temp is not None:
            row = [
                time.strftime("%Y-%m-%d %H:%M:%S"),
                motion_val,
                flame_val,
                gas_val,
                round(flow_rate, 3),
                round(b_temp, 2),
                round(b_hum, 2),
                round(b_pres, 2),
                round(dht_temp, 2),
                round(dht_hum, 2),
                is_alert
            ]
            with open(csv_file, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

        # -------- CONSOLE OUTPUT --------
        baseline_status = " | ".join(baseline_alerts) if baseline_alerts else "NORMAL"
        print(f"\n[{time.strftime('%H:%M:%S')}] STATUS: {baseline_status}")
        print(f"Motion: {motion_val} | Flame: {flame_val} | Gas: {gas_val} | Flow: {flow_rate:.2f} L/min")
        print(f"BME280: {b_temp:.1f}C, {b_hum:.1f}%, {b_pres:.1f}hPa")
        if dht_temp: print(f"DHT22:  {dht_temp:.1f}C, {dht_hum:.1f}%")
        
        # Log every 2 seconds to balance data quality and file size
        time.sleep(2.0)

except KeyboardInterrupt:
    print("\nStopping and cleaning up...")

finally:
    buzzer.off()
    dht_device.exit()