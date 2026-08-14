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


def build_message(device_id: str) -> dict[str, object]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": device_id,
        "temperature": round(random.uniform(18.0, 28.0), 2),
        "humidity": round(random.uniform(35.0, 65.0), 2),
        "voltage": round(random.uniform(3.1, 3.4), 3),
        "message_type": "normal",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="iot/sensors")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    connect_with_retry(client, args.host, args.port)

    device_ids = ["sensor-001", "sensor-002", "sensor-003"]
    while True:
        payload = build_message(random.choice(device_ids))
        client.publish(args.topic, json.dumps(payload))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
