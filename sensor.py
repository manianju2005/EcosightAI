import time
import board
import busio
import adafruit_dht
import adafruit_bme280.basic as adafruit_bme280
import RPi.GPIO as GPIO

# ---------------- PIR ----------------
PIR_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

# ---------------- DHT22 ----------------
# DHT22 को सेटअप करें
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

# ---------------- BME280 ----------------
i2c = busio.I2C(board.SCL, board.SDA)
# यहाँ address=0x76 बिल्कुल सही है
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# सेटिंग्स को नंबर्स के साथ सेट करें (ताकि Attribute Error न आए)
bme280.mode = 3            # 3 = MODE_NORMAL
bme280.filter = 16          # 16 = IIR_FILTER_X16
bme280.overscan_temperature = 2  # 2 = OVERSCAN_X2
bme280.overscan_humidity = 2     # 2 = OVERSCAN_X2
bme280.overscan_pressure = 2     # 2 = OVERSCAN_X2

print("--- System Starting ---")
print("Waiting for PIR to stabilize (30s)...")
time.sleep(30)
print("System Ready!")

try:
    while True:
        # -------- PIR --------
        motion = GPIO.input(PIR_PIN)
        status = "🚶 Motion Detected!" if motion else "No Motion"
        
        # -------- DHT22 --------
        dht_out = "DHT22: Reading..."
        try:
            temp_d = dht.temperature
            hum_d = dht.humidity
            if temp_d is not None:
                dht_out = f"DHT22 -> Temp: {temp_d:.1f}°C  Hum: {hum_d:.1f}%"
        except RuntimeError:
            dht_out = "DHT22: Reading error (Normal)"

        # -------- BME280 --------
        try:
            bme_temp = bme280.temperature
            bme_hum = bme280.humidity
            bme_press = bme280.pressure
            bme_out = f"BME280 -> Temp: {bme_temp:.1f}°C  Hum: {bme_hum:.1f}%  Pres: {bme_press:.1f}hPa"
        except Exception as e:
            bme_out = f"BME280 Error: {e}"

        # Print all data
        print(f"{status} | {dht_out}")
        print(bme_out)
        print("-" * 60)
        
        time.sleep(10)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    GPIO.cleanup()
    dht.exit()