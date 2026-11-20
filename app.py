import streamlit as st
import paho.mqtt.client as mqtt
import json
from collections import deque

# --- Configuration ---
MQTT_BROKER = "localhost"  # REMEMBER TO CHANGE THIS TO YOUR PI'S IP ADDRESS
MQTT_PORT = 1883
MQTT_TOPIC = "industrial/sensors"
HISTORY_LENGTH = 100  # Number of data points to display on the live graphs

# --- 1. In-Memory Data Store ---
@st.cache_resource
def get_data_store():
    return {
        'temp_history': deque(maxlen=HISTORY_LENGTH),
        'pressure_history': deque(maxlen=HISTORY_LENGTH),
        'latest': {
            'temperature': 0.0,
            'humidity': 0.0,
            'pressure': 0.0,
            'water_flow': 0.0,
            'air_quality': 0,  
            'flame': False,
            'motion': False,
            'risk_score': 0,
            'system_state': "WAITING..."
        }
    }

data_store = get_data_store()

# --- 2. Background MQTT Listener ---
@st.cache_resource
def init_mqtt():
    def on_connect(client, userdata, flags, rc):
        client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # Update history deques for the live graphs
            if 'temperature' in payload:
                data_store['temp_history'].append(payload['temperature'])
            if 'pressure' in payload:
                data_store['pressure_history'].append(payload['pressure'])
                
            # Update latest single-value metrics
            for key in data_store['latest'].keys():
                if key in payload:
                    data_store['latest'][key] = payload[key]
                    
        except Exception:
            pass # Ignore malformed JSON

    # Explicitly using VERSION1 to prevent the ValueError you encountered earlier
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Streamlit_Live_Dashboard")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start() 
    return client

init_mqtt()

# --- 3. Streamlit UI Layout ---
st.set_page_config(page_title="AI Sensor Fusion Dashboard", layout="wide")
st.title("🏭 Real-Time Industrial Monitoring")

# --- 4. Auto-Refreshing Live View ---
@st.fragment(run_every="1s")
def render_dashboard():
    latest = data_store['latest']
    
    # ROW 1: AI Sensor Fusion Status
    st.subheader("System Status")
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        state = latest['system_state']
        if state == "SAFE":
            st.success(f"✅ State: {state}")
        elif state in ["WARNING", "HIGH_RISK"]:
            st.warning(f"⚠️ State: {state}")
        elif state == "CRITICAL":
            st.error(f"🚨 State: {state}")
        else:
            st.info(f"State: {state}")
            
    with status_col2:
        st.metric("Fusion Risk Score", f"{latest['risk_score']} / 100")
        
    st.markdown("---")

    # ROW 2: Live Scrolling Graphs
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("🌡️ Temperature vs Time (°C)")
        if len(data_store['temp_history']) > 0:
            st.line_chart(list(data_store['temp_history']), height=250)
        else:
            st.write("Waiting for temperature data...")
            
    with chart_col2:
        st.subheader("⏱️ Atmospheric Pressure vs Time (hPa)")
        if len(data_store['pressure_history']) > 0:
            st.line_chart(list(data_store['pressure_history']), height=250)
        else:
            st.write("Waiting for pressure data...")

    st.markdown("---")
    
    # ROW 3: Critical Safety Alerts (Digital Sensors)
    st.subheader("Critical Alerts")
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        if latest['flame']:
            st.error("🔥 ALARM: FLAME DETECTED")
        else:
            st.success("✅ Fire System: Clear")
            
    with alert_col2:
        if latest['motion']:
            st.warning("🚶 ALARM: MOTION DETECTED")
        else:
            st.info("Motion System: Clear")

    st.markdown("---")

    # ROW 4: Current Environmental Metrics
    st.subheader("Current Environmental Readings")
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("🌡️ Temp (BME280)", f"{latest['temperature']} °C")
    m2.metric("💧 Humidity", f"{latest['humidity']} %")
    m3.metric("🌊 Water Flow", f"{latest['water_flow']} L/min")
    
    # Based on your hardware code, gas is read as a digital 0 or 1
    gas_status = "Detected" if latest['air_quality'] == 1 else "Normal"
    m4.metric("☁️ Gas Level (MQ135)", gas_status)

render_dashboard()