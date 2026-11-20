import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button
import threading

# ---------------- GPIO Setup ----------------
pir = DigitalInputDevice(17)
flow_sensor = Button(27, pull_up=True)
flame_sensor = DigitalInputDevice(18)
mq135 = DigitalInputDevice(24)

# DHT22 Setup
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# BME280 Setup
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# Global variables for DHT (Background Thread)
dht_temp, dht_hum = None, None

def read_dht_background():
    global dht_temp, dht_hum
    while True:
        try:
            dht_temp = dht_device.temperature
            dht_hum = dht_device.humidity
        except:
            pass
        time.sleep(3) # Background reading every 3 seconds

threading.Thread(target=read_dht_background, daemon=True).start()

# Flow Counter Logic
pulse_count = 0
def count_pulse():
    global pulse_count
    pulse_count += 1
flow_sensor.when_pressed = count_pulse

print("--- Industrial Monitoring System (Full Data) ---")
print("PIR stabilizing... Please wait.")
time.sleep(10)
print("System Ready!")

last_time = time.time()

try:
    while True:
        # 1. Fast Sensors Polling (Real-time)
        motion_val = pir.value
        pir_status = "🚶 MOTION!" if motion_val else "No Motion"
        flame = "🔥 FLAME! detected" if  flame_sensor.value else "Safe no fire"
        gas = "⚠️ GAS present!" if not mq135.value else "Clean air"
        
        # 2. Water Flow Calculation
        current_time = time.time()
        elapsed = current_time - last_time
        flow_rate = (pulse_count / elapsed / 7.5) if elapsed > 0 else 0
        pulse_count = 0
        last_time = current_time

        # 3. BME280 Data (Temperature, Humidity, and Pressure)
        try:
            b_temp = bme280.temperature
            b_hum = bme280.humidity
            b_pres = bme280.pressure    # <--- Pressure yahan add kiya hai
        except:
            b_temp, b_hum, b_pres = 0, 0, 0

        # --- OUTPUT DISPLAY ---
        print(f"\n[SECURITY] {pir_status} | {flame} | {gas}")
        print(f"[FLOW]     Rate: {flow_rate:.2f} L/min")
        
        # Environmental Data
        if b_temp:
            # Pressure hPa (hectopascals) mein show hoga
            print(f"[BME280]   T: {b_temp:.1f}°C | H: {b_hum:.1f}% | P: {b_pres:.1f}hPa")
        
        if dht_temp:
            print(f"[DHT22]    T: {dht_temp:.1f}°C | H: {dht_hum:.1f}%")
        else:
            print("[DHT22]    Reading (Background)...")

        print("-" * 65)
        
        # Loop delay 0.2s for high-speed response
        time.sleep(0.2) 

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    dht_device.exit()