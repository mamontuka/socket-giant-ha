import time
import json
import os
import requests
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt
import yaml

# === Load Configuration ===
def load_config():
    if os.path.exists("/data/options.json"):
        print("[CONFIG] Loading from /data/options.json")
        with open("/data/options.json", "r") as f:
            return json.load(f)
    elif os.path.exists("config.yaml"):
        print("[CONFIG] Loading from config.yaml")
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f).get("options", {})
    else:
        raise FileNotFoundError("No config file found")

config = load_config()

# === Configuration Variables ===
DEVICE_IP       = config["relay_ip"]
DEVICE_PORT     = config.get("relay_port", 80)
USERNAME        = config["relay_login"]
PASSWORD        = config["relay_password"]
NUM_RELAYS      = config.get("relay_count", 16)
INVERTED_RELAYS = config.get("inverted_relays", list(range(NUM_RELAYS)))
POLL_INTERVAL   = config.get("relay_poll_interval", 2)

MQTT_BROKER     = config["mqtt_broker"]
MQTT_PORT       = config.get("mqtt_port", 1883)
MQTT_USERNAME   = config.get("mqtt_username")
MQTT_PASSWORD   = config.get("mqtt_password")

# Get dynamic device ID and friendly name from config
DEVICE_ID       = config.get("device_id", "socket_giant_1")
FRIENDLY_NAME   = config.get("friendly_name", f"Socket Giant 1")

#MQTT_PREFIX     = f"homeassistant/{DEVICE_ID}"
MQTT_PREFIX     = f"homeassistant/socket_giant/{DEVICE_ID}"

# === Relay Status Polling ===
def get_relay_states():
    try:
        url = f"http://{DEVICE_IP}:{DEVICE_PORT}/protect/status.xml"
        r = requests.get(url, auth=(USERNAME, PASSWORD), timeout=5)
        xml = ET.fromstring(r.text)
        states = {}
        for i in range(NUM_RELAYS):
            raw = xml.find(f"./led{i}").text.strip()
            state = "ON" if raw == "1" else "OFF"
            if i in INVERTED_RELAYS:
                state = "OFF" if state == "ON" else "ON"
            states[i] = state
        return states
    except Exception as e:
        print(f"[ERROR] Could not fetch status: {e}")
        return {}

# === Relay Toggle ===
def set_relay(index, state):
    try:
        url = f"http://{DEVICE_IP}/protect/leds.cgi?led={index}"
        r = requests.get(url, auth=(USERNAME, PASSWORD), timeout=5)
        print(f"[CMD] Toggled relay {index}, response: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to toggle relay {index}: {e}")

# === MQTT Setup ===
def announce_device_and_switches(client):
    # Announce main device
    device_config_topic = f"{MQTT_PREFIX}/config"
    payload = {
        "name": FRIENDLY_NAME,
        "unique_id": DEVICE_ID,
        "device": {
            "identifiers": [DEVICE_ID],
            "name": FRIENDLY_NAME,
            "model": "Socket Giant",
            "manufacturer": "VKModules"
        }
    }
    client.publish(device_config_topic, json.dumps(payload), retain=True)
    print(f"[MQTT] Announced device {DEVICE_ID} as {FRIENDLY_NAME}")

    # Announce relays as switches
    for i in range(NUM_RELAYS):
        unique_id = f"{DEVICE_ID}_relay_{i}"
        config_topic = f"homeassistant/switch/{DEVICE_ID}/relay{i}/config"
        relay_payload = {
            "name": f"RL-{i+1}",
            "state_topic": f"{MQTT_PREFIX}/relay{i}/state",
            "command_topic": f"{MQTT_PREFIX}/relay{i}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"{MQTT_PREFIX}/relay{i}/availability",
            "unique_id": f"{DEVICE_ID}_rl_{i+1}",
            "device": {
                "identifiers": [DEVICE_ID],
                "name": FRIENDLY_NAME,
                "model": "Socket Giant",
                "manufacturer": "VKModules"
            }
        }
        client.publish(config_topic, json.dumps(relay_payload), retain=True)
        client.subscribe(relay_payload["command_topic"])
        client.publish(relay_payload["state_topic"], "OFF", retain=True)
        client.publish(relay_payload["availability_topic"], "online", retain=True)
        print(f"[MQTT] Announced relay {i}")

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")
    announce_device_and_switches(client)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().upper()
    print(f"[MQTT] Received {topic}: {payload}")

    if topic.endswith("/set"):
        try:
            idx = int(topic.split("/")[-2].replace("relay", ""))
            if idx in INVERTED_RELAYS:
                payload = "OFF" if payload == "ON" else "ON"
            set_relay(idx, payload)
        except Exception as e:
            print(f"[ERROR] Processing command: {e}")

# === MQTT Init ===
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

client.will_set(f"{MQTT_PREFIX}/bridge/status", "offline", retain=True)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# === Main Loop ===
try:
    client.publish(f"{MQTT_PREFIX}/bridge/status", "online", retain=True)
    while True:
        states = get_relay_states()
        for i, state in states.items():
            client.publish(f"{MQTT_PREFIX}/relay{i}/state", state, retain=True)
        time.sleep(POLL_INTERVAL)
except KeyboardInterrupt:
    print("Stopping bridge...")
finally:
    client.publish(f"{MQTT_PREFIX}/bridge/status", "offline", retain=True)
    client.loop_stop()
