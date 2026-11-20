import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
import json
import paho.mqtt.publish as publish

from gpiozero import DigitalInputDevice, Button, Buzzer

import threading
from collections import deque
import numpy as np
import csv
import os


# ============================================================
# 1. GPIO SETUP
# ============================================================

pir = DigitalInputDevice(17)
flow_sensor = Button(27, pull_up=True)
flame_sensor = DigitalInputDevice(18)
mq135 = DigitalInputDevice(24)

buzzer = Buzzer(26)


# ============================================================
# 2. DHT22 SETUP
# ============================================================

DHT_PIN = board.D22

dht_device = adafruit_dht.DHT22(
    DHT_PIN,
    use_pulseio=False
)


# ============================================================
# 3. BME280 SETUP
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)

bme280 = adafruit_bme280.Adafruit_BME280_I2C(
    i2c,
    address=0x76
)


# ============================================================
# 4. CSV FILE
# ============================================================

csv_file = "/home/gaurav/iotiot-venv/sensor_fusion_data.csv"

headers = [
    "timestamp",

    # Raw sensor values
    "motion",
    "flame",
    "gas",
    "flow_rate",

    "bme_temp",
    "bme_hum",
    "bme_pres",

    "dht_temp",
    "dht_hum",

    # Fusion / derived features
    "temp_avg",
    "humidity_avg",

    "gas_mean",
    "gas_std",

    "temp_mean",
    "temp_std",

    "flow_mean",
    "flow_std",

    "gas_change",
    "temp_change",
    "flow_change",

    # Sensor fusion score
    "risk_score",

    # Final state
    "system_state"
]


if not os.path.isfile(csv_file):

    with open(csv_file, mode="w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(headers)


# ============================================================
# 5. DHT22 BACKGROUND THREAD
# ============================================================

dht_temp = None
dht_hum = None


def read_dht_background():

    global dht_temp
    global dht_hum

    while True:

        try:

            dht_temp = dht_device.temperature
            dht_hum = dht_device.humidity

        except Exception:
            pass

        time.sleep(3)


threading.Thread(
    target=read_dht_background,
    daemon=True
).start()


# ============================================================
# 6. WATER FLOW PULSE COUNTER
# ============================================================

pulse_count = 0


def count_pulse():

    global pulse_count

    pulse_count += 1


flow_sensor.when_pressed = count_pulse


# ============================================================
# 7. SENSOR HISTORY
# ============================================================

WINDOW_SIZE = 30

gas_history = deque(maxlen=WINDOW_SIZE)
temp_history = deque(maxlen=WINDOW_SIZE)
flow_history = deque(maxlen=WINDOW_SIZE)


# ============================================================
# 8. HELPER FUNCTION
# ============================================================

def safe_mean(data):

    if len(data) == 0:
        return 0

    return np.mean(data)


def safe_std(data):

    if len(data) < 2:
        return 0

    return np.std(data)


# ============================================================
# 9. SENSOR FUSION
# ============================================================

def sensor_fusion(
    motion,
    flame,
    gas,
    flow_rate,
    bme_temp,
    bme_hum,
    bme_pres,
    dht_temp,
    dht_hum
):

    """
    Combines all sensor information and generates
    a risk score.

    NOTE:
    This is a preliminary fusion model.
    Later, the manually defined risk score can be
    replaced by a trained ML model.
    """

    risk_score = 0


    # --------------------------------------------------------
    # FIRE / FLAME
    # --------------------------------------------------------

    if flame == 1:

        risk_score += 40


    # --------------------------------------------------------
    # GAS / SMOKE
    # --------------------------------------------------------

    if gas == 1:

        risk_score += 25


    # --------------------------------------------------------
    # TEMPERATURE
    # --------------------------------------------------------

    if bme_temp > 40:

        risk_score += 15


    if bme_temp > 50:

        risk_score += 10


    # --------------------------------------------------------
    # WATER FLOW
    # --------------------------------------------------------

    if flow_rate > 5:

        risk_score += 10


    # --------------------------------------------------------
    # MOTION
    # --------------------------------------------------------

    if motion == 1:

        risk_score += 5


    # --------------------------------------------------------
    # SENSOR FUSION
    # --------------------------------------------------------

    # Gas + high temperature
    if gas == 1 and bme_temp > 35:

        risk_score += 10


    # Gas + flame
    if gas == 1 and flame == 1:

        risk_score += 20


    # Flame + high temperature
    if flame == 1 and bme_temp > 35:

        risk_score += 15


    # Gas + flame + high temperature
    if (
        gas == 1
        and flame == 1
        and bme_temp > 35
    ):

        risk_score += 20


    # Limit score to 100

    risk_score = min(risk_score, 100)


    # --------------------------------------------------------
    # CLASSIFY RISK
    # --------------------------------------------------------

    if risk_score < 30:

        state = "SAFE"

    elif risk_score < 60:

        state = "WARNING"

    elif risk_score < 80:

        state = "HIGH_RISK"

    else:

        state = "CRITICAL"


    return risk_score, state


# ============================================================
# 10. SYSTEM START
# ============================================================

print("\n==========================================")
print(" AI MULTI-SENSOR FUSION SYSTEM")
print("==========================================")

print("CSV file:")
print(csv_file)

print("\nPIR stabilizing...")

time.sleep(10)

print("System Ready!\n")


# ============================================================
# 11. FLOW CALCULATION
# ============================================================

last_time = time.time()


# ============================================================
# 12. MAIN LOOP
# ============================================================

try:

    while True:

        # ====================================================
        # A. READ FAST SENSORS
        # ====================================================

        motion = int(pir.value)

        flame = int(flame_sensor.value)

        # Your current MQ135 setup is DIGITAL
        gas = 0 if mq135.value else 1


        # ====================================================
        # B. WATER FLOW
        # ====================================================

        current_time = time.time()

        elapsed = current_time - last_time


        if elapsed > 0:

            flow_rate = (
                pulse_count
                / elapsed
                / 7.5
            )

        else:

            flow_rate = 0


        pulse_count = 0

        last_time = current_time


        # ====================================================
        # C. BME280
        # ====================================================

        try:

            bme_temp = bme280.temperature

            bme_hum = bme280.humidity

            bme_pres = bme280.pressure

        except Exception:

            bme_temp = 0

            bme_hum = 0

            bme_pres = 0


        # ====================================================
        # D. DHT22
        # ====================================================

        current_dht_temp = dht_temp

        current_dht_hum = dht_hum


        if current_dht_temp is None:

            current_dht_temp = bme_temp


        if current_dht_hum is None:

            current_dht_hum = bme_hum


        # ====================================================
        # E. UPDATE SENSOR HISTORY
        # ====================================================

        gas_history.append(gas)

        temp_history.append(bme_temp)

        flow_history.append(flow_rate)


        # ====================================================
        # F. CALCULATE STATISTICAL FEATURES
        # ====================================================

        gas_mean = safe_mean(gas_history)

        gas_std = safe_std(gas_history)


        temp_mean = safe_mean(temp_history)

        temp_std = safe_std(temp_history)


        flow_mean = safe_mean(flow_history)

        flow_std = safe_std(flow_history)


        # ====================================================
        # G. RATE OF CHANGE
        # ====================================================

        if len(gas_history) >= 2:

            gas_change = (
                gas_history[-1]
                - gas_history[-2]
            )

        else:

            gas_change = 0


        if len(temp_history) >= 2:

            temp_change = (
                temp_history[-1]
                - temp_history[-2]
            )

        else:

            temp_change = 0


        if len(flow_history) >= 2:

            flow_change = (
                flow_history[-1]
                - flow_history[-2]
            )

        else:

            flow_change = 0


        # ====================================================
        # H. SENSOR FUSION
        # ====================================================

        risk_score, system_state = sensor_fusion(

            motion,
            flame,
            gas,
            flow_rate,

            bme_temp,
            bme_hum,
            bme_pres,

            current_dht_temp,
            current_dht_hum
        )


        # ====================================================
        # I. TEMPERATURE / HUMIDITY FUSION
        # ====================================================

        temp_avg = (
            bme_temp + current_dht_temp
        ) / 2


        humidity_avg = (
            bme_hum + current_dht_hum
        ) / 2


        # ====================================================
        # J. BUZZER
        # ====================================================

        if risk_score >= 60:

            buzzer.on()

        else:

            buzzer.off()


        # ====================================================
        # K. SAVE DATA
        # ====================================================

        row = [

            time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            motion,
            flame,
            gas,

            round(flow_rate, 3),

            round(bme_temp, 2),
            round(bme_hum, 2),
            round(bme_pres, 2),

            round(current_dht_temp, 2),
            round(current_dht_hum, 2),

            round(temp_avg, 2),
            round(humidity_avg, 2),

            round(gas_mean, 4),
            round(gas_std, 4),

            round(temp_mean, 2),
            round(temp_std, 2),

            round(flow_mean, 3),
            round(flow_std, 3),

            round(gas_change, 4),
            round(temp_change, 4),
            round(flow_change, 4),

            risk_score,

            system_state
        ]


        with open(
            csv_file,
            mode="a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow(row)
        
        # Ensure these variables match the exact names used earlier in your loop
        payload = {
            "temperature": round(bme_temp, 2),
            "humidity": round(bme_hum, 2),
            "pressure": round(bme_pres, 2),
            "air_quality": gas, 
            "water_flow": round(flow_rate, 2),
            "flame": True if flame == 1 else False,
            "motion": True if motion == 1 else False,
            "risk_score": risk_score,
            "system_state": system_state
        }
        
        # Broadcast the JSON payload to the local Mosquitto broker
        try:
            publish.single("industrial/sensors", payload=json.dumps(payload), hostname="localhost")
        except Exception as e:
            print(f"MQTT Publish Error: {e}")


        # ====================================================
        # L. DISPLAY
        # ====================================================

        print("\n------------------------------------------")

        print(
            f"[{time.strftime('%H:%M:%S')}]"
        )

        print(
            f"Motion      : {motion}"
        )

        print(
            f"Flame       : {flame}"
        )

        print(
            f"Gas         : {gas}"
        )

        print(
            f"Water Flow  : {flow_rate:.2f} L/min"
        )

        print(
            f"BME Temp    : {bme_temp:.2f} °C"
        )

        print(
            f"BME Humidity: {bme_hum:.2f} %"
        )

        print(
            f"BME Pressure: {bme_pres:.2f} hPa"
        )

        print(
            f"DHT Temp    : {current_dht_temp:.2f} °C"
        )

        print(
            f"DHT Humidity: {current_dht_hum:.2f} %"
        )

        print("------------------------------------------")

        print(
            f"Temperature Average : {temp_avg:.2f} °C"
        )

        print(
            f"Humidity Average    : {humidity_avg:.2f} %"
        )

        print(
            f"Gas Change          : {gas_change:.4f}"
        )

        print(
            f"Temperature Change  : {temp_change:.4f}"
        )

        print(
            f"Flow Change         : {flow_change:.4f}"
        )

        print("------------------------------------------")

        print(
            f"FUSED RISK SCORE : {risk_score}/100"
        )

        print(
            f"SYSTEM STATE     : {system_state}"
        )

        print("------------------------------------------")


        # ====================================================
        # M. SAMPLING INTERVAL
        # ====================================================

        time.sleep(2)


except KeyboardInterrupt:

    print("\nStopping system...")


finally:

    buzzer.off()

    dht_device.exit()

    print("System stopped.")