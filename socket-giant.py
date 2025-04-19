import time
import json
import os
import requests
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt
import yaml
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

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
print("[DEBUG] Loaded relay boards config:")
for b in config["relay_boards"]:
    print(f"  - {b['device_id']} enabled={b.get('enabled', True)}")

# === Configuration Variables ===
MQTT_BROKER     = config["mqtt_broker"]
MQTT_PORT       = config.get("mqtt_port", 1883)
MQTT_USERNAME   = config.get("mqtt_username")
MQTT_PASSWORD   = config.get("mqtt_password")

POLL_INTERVAL   = config.get("relay_poll_interval", 2)

# === Relay Status Polling ===
def get_relay_states(board_config):
    if not board_config.get("enabled", True):  # Skip disabled boards
        print(f"[SKIP] Skipping disabled board {board_config['device_id']}")
        return {}

    try:
        url = f"http://{board_config['relay_ip']}:{board_config['relay_port']}/protect/status.xml"
 #       print(f"[INFO] Fetching status from {url}")
        r = requests.get(url, auth=(board_config['relay_login'], board_config['relay_password']), timeout=2)
        r.raise_for_status()  # Raise an exception if the status code is not 200
        xml = ET.fromstring(r.text)
        states = {}
        num_relays = len(board_config['inverted_relays'])
        for i in range(num_relays):
            raw = xml.find(f"./led{i}").text.strip()
            state = "ON" if raw == "1" else "OFF"
            if i in board_config['inverted_relays']:
                state = "OFF" if state == "ON" else "ON"
            states[i] = state
        return states
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not fetch status for {board_config['device_id']}: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] Unexpected error for {board_config['device_id']}: {e}")
        return {}


# === Relay Toggle ===
def set_relay(board_config, index, state):
    try:
        url = f"http://{board_config['relay_ip']}/protect/leds.cgi?led={index}"
        r = requests.get(url, auth=(board_config['relay_login'], board_config['relay_password']), timeout=5)
        print(f"[CMD] Toggled relay {index} for {board_config['device_id']}, response: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to toggle relay {index} for {board_config['device_id']}: {e}")

# === MQTT Setup ===
def announce_device_and_switches(client, board_config):
    if not board_config.get("enabled", True):
        print(f"[SKIP] Skipping disabled board {board_config['device_id']}")
        return

    # Announce main device
    device_config_topic = f"homeassistant/socket_giant/{board_config['device_id']}/config"
    payload = {
        "name": board_config["friendly_name"],
        "unique_id": board_config["device_id"],
        "device": {
            "identifiers": [board_config["device_id"]],
            "name": board_config["friendly_name"],
            "model": "Socket Giant",
            "manufacturer": "VKmodule"
        }
    }
    client.publish(device_config_topic, json.dumps(payload), retain=True)
    print(f"[MQTT] Announced device {board_config['device_id']} as {board_config['friendly_name']}")

    # Announce relays as switches
    num_relays = board_config["relay_count"]  # Update here to use relay_count
    for i in range(num_relays):
        unique_id = f"{board_config['device_id']}_relay_{i}"
        config_topic = f"homeassistant/switch/{board_config['device_id']}/relay{i}/config"
        relay_payload = {
            "name": f"RL-{i+1}",
            "state_topic": f"homeassistant/socket_giant/{board_config['device_id']}/relay{i}/state",
            "command_topic": f"homeassistant/socket_giant/{board_config['device_id']}/relay{i}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"homeassistant/socket_giant/{board_config['device_id']}/relay{i}/availability",
            "unique_id": f"{board_config['device_id']}_rl_{i+1}",
            "device": {
                "identifiers": [board_config['device_id']],
                "name": board_config['friendly_name'],
                "model": "Socket Giant",
                "manufacturer": "VKmodule"
            }
        }
        client.publish(config_topic, json.dumps(relay_payload), retain=True)
        client.subscribe(relay_payload["command_topic"])
        client.publish(relay_payload["state_topic"], "OFF", retain=True)
        client.publish(relay_payload["availability_topic"], "online", retain=True)
        print(f"[MQTT] Announced relay {i} for {board_config['device_id']}")

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")
    for board_config in config["relay_boards"]:
        if not board_config.get("enabled", True):
            print(f"[SKIP] Skipping disabled board {board_config['device_id']}")
            continue
        announce_device_and_switches(client, board_config)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().upper()
    print(f"[MQTT] Received {topic}: {payload}")

    if topic.endswith("/set"):
        try:
            board_id = topic.split("/")[2]
            idx = int(topic.split("/")[-2].replace("relay", ""))
            for board_config in config["relay_boards"]:
                if board_config["device_id"] == board_id:
                    if idx in board_config['inverted_relays']:
                        payload = "OFF" if payload == "ON" else "ON"
                    set_relay(board_config, idx, payload)
                    break
        except Exception as e:
            print(f"[ERROR] Processing command: {e}")

# === MQTT Init ===
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

client.will_set(f"homeassistant/socket_giant/bridge/status", "offline", retain=True)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# === Main Loop ===
try:
    while True:
        for board_config in config["relay_boards"]:
            if not board_config.get("enabled", True):
                continue

            # Only try to fetch the status if the board is enabled
            states = get_relay_states(board_config)
            for i, state in states.items():
                client.publish(f"homeassistant/socket_giant/{board_config['device_id']}/relay{i}/state", state, retain=True)
        time.sleep(POLL_INTERVAL)
except KeyboardInterrupt:
    print("Stopping bridge...")
finally:
    client.publish(f"homeassistant/socket_giant/bridge/status", "offline", retain=True)
    client.loop_stop()
