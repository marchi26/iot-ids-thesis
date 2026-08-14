from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import paho.mqtt.client as mqtt


FIELDNAMES = [
    "timestamp",
    "device_id",
    "temperature",
    "humidity",
    "voltage",
    "message_type",
    "attack_type",
]


def connect_with_retry(client: mqtt.Client, host: str, port: int, retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.connect(host, port)
            return
        except OSError:
            if attempt == retries:
                raise
            time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="iot/sensors")
    parser.add_argument("--output", default="results/metrics/simulated_iot_traffic.csv")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not output_path.exists()
    output_file = output_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
    if is_new:
        writer.writeheader()
        output_file.flush()

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            return
        row = {field: payload.get(field, "") for field in FIELDNAMES}
        writer.writerow(row)
        output_file.flush()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    connect_with_retry(client, args.host, args.port)
    client.subscribe(args.topic)
    client.loop_forever()


if __name__ == "__main__":
    main()
