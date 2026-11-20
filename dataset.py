import pandas as pd
import random

data = []

for _ in range(1000):
    # Sensor values
    bme_temp = random.uniform(-5, 65)
    bme_hum  = random.uniform(5, 100)
    pressure = random.uniform(980, 1025)

    dht_temp = random.uniform(-10, 80)
    dht_hum  = random.uniform(5, 100)

    flow = random.uniform(0, 60)

    pir   = random.choice([0, 1])   # 1 = motion
    flame = random.choice([0, 1])   # 1 = fire
    gas   = random.choice([0, 1])   # 0 = gas leak

    # Anomaly labeling logic
    label = 1 if (
        bme_temp > 40 or
        dht_temp > 45 or
        bme_hum > 90 or
        dht_hum > 90 or
        pressure < 985 or pressure > 1020 or
        flow > 15 or
        flame == 1 or
        gas == 0
    ) else 0

    data.append([
        bme_temp, bme_hum, pressure,
        dht_temp, dht_hum,
        flow, pir, flame, gas, label
    ])

df = pd.DataFrame(data, columns=[
    "bme_temp","bme_hum","bme_pressure",
    "dht_temp","dht_hum",
    "flow_rate","pir","flame","gas","label"
])

df.to_csv("iot_extreme_dataset.csv", index=False)
df.to_excel("iot_extreme_dataset.xlsx", index=False)

print("Dataset saved successfully!")
