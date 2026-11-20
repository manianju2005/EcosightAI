import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
from gpiozero import DigitalInputDevice, Button

# ---------------- GPIO Setup (Modern Way) ----------------
# PIR Sensor
pir = DigitalInputDevice(17)

# Flow Sensor (YF-S201)
# Button class use kar rahe hain kyunki ye interrupts handle karna asaan banata hai
flow_sensor = Button(27, pull_up=True)

pulse_count = 0

def count_pulse():
    global pulse_count
    pulse_count += 1

# Interrupt attach karein
flow_sensor.when_pressed = count_pulse

# ---------------- DHT22 ----------------
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

# ---------------- BME280 ----------------
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

print("--- System Starting ---")
print("Waiting for sensors to stabilize...")
time.sleep(5) # 30s is long, 5-10s is usually enough for testing
print("System Ready!")

try:
    last_time = time.time()
    while True:
        # -------- Water Flow Calculation --------
        current_time = time.time()
        elapsed_time = current_time - last_time
        
        if elapsed_time > 0:
            flow_hz = pulse_count / elapsed_time
            flow_rate = flow_hz / 7.5
        else:
            flow_rate = 0
        
        pulse_count = 0
        last_time = current_time

        # -------- PIR --------
        status = "🚶 Motion Detected!" if pir.value else "No Motion"
        
        # -------- DHT22 --------
        dht_out = "DHT22 Error"
        try:
            temp_d = dht.temperature
            hum_d = dht.humidity
            if temp_d is not None:
                dht_out = f"DHT22 -> T: {temp_d:.1f}C H: {hum_d:.1f}%"
        except RuntimeError:
            # DHT errors are common, just skip
            pass

        # -------- BME280 --------
        try:
            bme_temp = bme280.temperature
            bme_press = bme280.pressure
            bme_out = f"BME280 -> T: {bme_temp:.1f}C P: {bme_press:.1f}hPa"
        except Exception:
            bme_out = "BME280 Error"

        # -------- Display --------
        print(f"{status} | Flow: {flow_rate:.2f} L/min")
        print(f"{dht_out} | {bme_out}")
        print("-" * 65)
        
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    dht.exit()
    # gpiozero automatically cleans up, no need for GPIO.cleanup()