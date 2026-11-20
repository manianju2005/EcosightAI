import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button

# ---------------- GPIO Setup ----------------
pir = DigitalInputDevice(17)        # PIR: GPIO 17
flow_sensor = Button(27, pull_up=True) # Flow: GPIO 27
flame_sensor = DigitalInputDevice(18)  # Flame: GPIO 18
mq135 = DigitalInputDevice(24)      # MQ135 Gas Sensor: GPIO 24 (New)

# DHT22: GPIO 22
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# ---------------- Variables ----------------
pulse_count = 0
def count_pulse():
    global pulse_count
    pulse_count += 1

flow_sensor.when_pressed = count_pulse

# ---------------- BME280 Setup ----------------
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

print("--- System Starting ---")
print("Stabilizing sensors (MQ135 needs warm-up)...")
time.sleep(5) 
print("System Ready!")

last_time = time.time()

try:
    while True:
        # -------- Water Flow Calculation --------
        current_time = time.time()
        elapsed_time = current_time - last_time
        flow_rate = (pulse_count / elapsed_time / 7.5) if elapsed_time > 0 else 0
        pulse_count = 0 
        last_time = current_time

        # -------- PIR Motion --------
        pir_status = "🚶 Motion!" if pir.value else "No Motion"

        # -------- Flame Detection (Logic Inverted Fix) --------
        # Agar aag na hone par Flame Detected dikhaye, to 'not' hata dena
        flame_status = "🔥 FLAME!" if  flame_sensor.value else "Safe"

        # -------- MQ135 Gas Detection --------
        # DO pin 0 (LOW) deta hai jab gas detect hoti hai
        gas_status = "⚠️ Gas/Smoke!" if  mq135.value else "Air Clean"
        
        # -------- DHT22 (Retry Logic) --------
        try:
            t_d = dht_device.temperature
            h_d = dht_device.humidity
            dht_out = f"DHT22 -> T: {t_d:.1f}°C H: {h_d:.1f}%"
        except (RuntimeError, TypeError):
            dht_out = "DHT22: Wait..."
        
        time.sleep(1) # Gap for DHT stability

        # -------- BME280 --------
        try:
            bme_out = f"BME280 -> T: {bme280.temperature:.1f}°C P: {bme280.pressure:.1f}hPa H:{bme280.humidity:.1f}%"
        except:
            bme_out = "BME280: Error"

        # -------- Final Output --------
        print(f"{pir_status} | {flame_status} | {gas_status}")
        print(f"Flow Rate: {flow_rate:.2f} L/min")
        print(f"{dht_out} | {bme_out}")
        print("-" * 70)
        
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    dht_device.exit()
    print("GPIO Cleaned up.")