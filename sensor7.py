import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button, Buzzer  # Added Buzzer here
import threading
from collections import deque
import numpy as np

# ---------------- GPIO Setup ----------------
pir = DigitalInputDevice(17)
flow_sensor = Button(27, pull_up=True)
flame_sensor = DigitalInputDevice(18)
mq135 = DigitalInputDevice(24)
buzzer = Buzzer(26)  # Buzzer connected to GPIO 26

# DHT22 Setup
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# BME280 Setup
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

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
print("--- Industrial Monitoring System (Dynamic Baseline Enabled) ---")
print("PIR stabilizing... Please wait.")
time.sleep(10)
print("System Ready!")

last_time = time.time()

try:
    while True:
        # -------- FAST SENSOR READ --------
        motion_val = pir.value
        flame_val = flame_sensor.value
        # MQ135: Digital LOW (0) usually means gas detected
        gas_val = 0 if not mq135.value else 1   

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

        # -------- BUZZER & ALERT LOGIC --------
        # Trigger if Motion detected OR Flame detected OR Gas detected (gas_val is 0 when detected)
        if motion_val or flame_val or gas_val == 0:
            buzzer.on()
        else:
            buzzer.off()

        baseline_alerts = []
        if temp_th and b_temp > temp_th:
            baseline_alerts.append("OVERHEAT")
        if flow_th and flow_rate > flow_th:
            baseline_alerts.append("WATER LEAK")
        if gas_th and gas_val < gas_th:
            baseline_alerts.append("GAS LEAK")

        baseline_status = " | ".join(baseline_alerts) if baseline_alerts else "NORMAL"

        # -------- OUTPUT --------
        print("\n================ CURRENT STATUS =================")
        print(f"[MOTION]   {'Detected !!' if motion_val else 'None'}")
        print(f"[FLAME]    {'Detected !!' if flame_val else 'Safe'}")
        print(f"[GAS]      {'Detected !!' if gas_val == 0 else 'Clean'}")
        print(f"[FLOW]     {flow_rate:.2f} L/min")
        print(f"[BME280]   T:{b_temp:.1f}°C  H:{b_hum:.1f}%  P:{b_pres:.1f}hPa")

        if dht_temp:
            print(f"[DHT22]   T:{dht_temp:.1f}°C  H:{dht_hum:.1f}%")
        else:
            print("[DHT22]   Reading...")

        print(f"[BASELINE ALERT] {baseline_status}")
        
        if buzzer.is_active:
            print("[ALARM]    BUZZER ACTIVE!")

        if temp_th:
            print(f"[THRESHOLDS] Temp>{temp_th:.1f}  Flow>{flow_th:.2f}")

        print("=================================================")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping system...")

finally:
    buzzer.off() # Ensure buzzer is off when script stops
    dht_device.exit()