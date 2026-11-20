import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button

# ---------------- GPIO Setup ----------------
pir = DigitalInputDevice(17)
flow_sensor = Button(27, pull_up=True)
flame_sensor = DigitalInputDevice(18)
mq135 = DigitalInputDevice(24)

# DHT22 Setup
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# ---------------- Flow Sensor Logic ----------------
pulse_count = 0
def count_pulse():
    global pulse_count
    pulse_count += 1
flow_sensor.when_pressed = count_pulse

# ---------------- BME280 Setup ----------------
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

def get_dht_data():
    """DHT22 reading with internal retries to avoid 'Wait' error"""
    for _ in range(5): # 5 baar koshish karega
        try:
            t = dht_device.temperature
            h = dht_device.humidity
            if t is not None and h is not None:
                return t, h
        except RuntimeError:
            time.sleep(0.1)
            continue
    return None, None

print("--- Industrial Monitoring System Starting ---")
print("Warming up sensors...")
time.sleep(5)
print("System Ready!")

last_time = time.time()

try:
    while True:
        # 1. Calculation for Water Flow
        current_time = time.time()
        elapsed = current_time - last_time
        flow_rate = (pulse_count / elapsed / 7.5) if elapsed > 0 else 0
        pulse_count = 0
        last_time = current_time

        # 2. Reading Digital Sensors
        motion = 1 if pir.value else 0
        flame = 1 if  flame_sensor.value else 0 # Logic inverted for safety
        gas = 1 if not mq135.value else 0          # Logic inverted for safety

        # 3. Reading Analog/Environmental Sensors
        d_temp, d_hum = get_dht_data()
        
        try:
            b_temp = bme280.temperature
            b_pres = bme280.pressure
            b_hum = bme280.humidity
        except:
            b_temp, b_pres, b_hum = None, None, None

        # 4. Preparing Data for AI/ML Model
        # Ye dictionary aapka 'Feature Vector' banegi ML ke liye
        sensor_data = {
            "temp": b_temp if b_temp else d_temp, # BME is primary
            "humidity": b_hum if b_hum else d_hum,
            "pressure": b_pres,
            "flow": flow_rate,
            "motion": motion,
            "flame": flame,
            "gas": gas
        }

        # 5. Output Display
        print(f"\n[SYSTEM STATUS]")
        print(f"Motion: {motion} | Flame: {flame} | Gas: {gas}")
        print(f"Flow: {flow_rate:.2f} L/min")
        
        if d_temp:
            print(f"DHT22 -> T: {d_temp:.1f}°C H: {d_hum:.1f}%")
        else:
            print("DHT22 -> Sensor Error (Retrying...)")
            
        if b_temp:
            print(f"BME280 -> T: {b_temp:.1f}°C P: {b_pres:.1f}hPa H: {b_hum:.1f}%")

        # 6. AI/ML Integration Placeholder
        # Yahan aap apna model.predict(sensor_data) call kar sakte hain
        print(f"AI Vector: {list(sensor_data.values())}")
        
        print("-" * 50)
        time.sleep(2) # Overall stability delay

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    dht_device.exit()
    print("Cleanup Complete.")