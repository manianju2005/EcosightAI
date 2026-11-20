import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button

# ---------------- GPIO Setup ----------------
# PIR Sensor: GPIO 17 (Physical Pin 11)
pir = DigitalInputDevice(17)

# Flow Sensor: GPIO 27 (Physical Pin 13)
flow_sensor = Button(27, pull_up=True)

# DHT22: GPIO 22 (Physical Pin 15) - Recommended to change from Pin 4
DHT_PIN = board.D22 
dht_device = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# ---------------- Variables ----------------
pulse_count = 0

def count_pulse():
    global pulse_count
    pulse_count += 1

# Interrupt for Flow Sensor
flow_sensor.when_pressed = count_pulse

# ---------------- BME280 Setup ----------------
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

print("--- System Starting ---")
print("Stabilizing sensors...")
time.sleep(5) 
print("System Ready! Press Ctrl+C to stop.")

last_time = time.time()

try:
    while True:
        # -------- Water Flow Calculation --------
        current_time = time.time()
        elapsed_time = current_time - last_time
        
        if elapsed_time > 0:
            # Formula: (Pulses / Seconds) / 7.5 = L/min
            flow_hz = pulse_count / elapsed_time
            flow_rate = flow_hz / 7.5
        else:
            flow_rate = 0
            
        pulse_count = 0 # Reset for next interval
        last_time = current_time

        # -------- PIR Motion --------
        status = "🚶 Motion Detected!" if pir.value else "No Motion"
        
        # -------- DHT22 (With Robust Error Handling) --------
        dht_out = "DHT22: Reading..."
        try:
            t_d = dht_device.temperature
            h_d = dht_device.humidity
            if t_d is not None and h_d is not None:
                dht_out = f"DHT22 -> T: {t_d:.1f}°C H: {h_d:.1f}%"
        except RuntimeError:
            # DHT errors are normal, don't crash the script
            dht_out = "DHT22: Wait..."
        except Exception as e:
            dht_out = f"DHT22: Error"
        time.sleep(4)    

        # -------- BME280 --------
        try:
            bme_t = bme280.temperature
            bme_p = bme280.pressure
            bme_h = bme280.humidity
            bme_out = f"BME280 -> T: {bme_t:.1f}°C P: {bme_p:.1f}hPa H:{bme_h:.1f} %"
        except:
            bme_out = "BME280: Error"

        # -------- Output --------
        print(f"{status} | Flow: {flow_rate:.2f} L/min")
        print(f"{dht_out} | {bme_out}")
        print("-" * 65)
        
        time.sleep(2) # DHT22 needs at least 2s gap

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Proper Cleanup
    dht_device.exit()
    print("GPIO Cleaned up.")