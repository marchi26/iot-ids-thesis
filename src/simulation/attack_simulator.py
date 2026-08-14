from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def connect_with_retry(client: mqtt.Client, host: str, port: int, retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.connect(host, port)
            return
        except OSError:
            if attempt == retries:
                raise
            time.sleep(delay)


def build_anomalous_message() -> dict[str, object]:
    attack_type = random.choice(["burst", "out_of_range_sensor", "spoofed_device"])
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": random.choice(["unknown-device", "sensor-001", "sensor-admin"]),
        "temperature": round(random.uniform(-20.0, 95.0), 2),
        "humidity": round(random.uniform(0.0, 100.0), 2),
        "voltage": round(random.uniform(1.0, 5.5), 3),
        "message_type": "anomaly",
        "attack_type": attack_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="iot/sensors")
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    connect_with_retry(client, args.host, args.port)

    while True:
        for _ in range(random.randint(3, 8)):
            client.publish(args.topic, json.dumps(build_anomalous_message()))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
