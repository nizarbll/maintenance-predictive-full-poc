#!/usr/bin/env python3
"""Simple consumer to verify engine-telemetry stream."""

from __future__ import annotations

import argparse
import json
import signal
import sys

from confluent_kafka import Consumer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consume engine telemetry from Kafka.")
    p.add_argument("--bootstrap-servers", default="localhost:29092")
    p.add_argument("--topic", default="engine-telemetry")
    p.add_argument("--group-id", default="nasa-telemetry-debug")
    p.add_argument("--from-beginning", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    conf = {
        "bootstrap.servers": args.bootstrap_servers,
        "group.id": args.group_id,
        "auto.offset.reset": "earliest" if args.from_beginning else "latest",
        "enable.auto.commit": True,
    }
    consumer = Consumer(conf)
    consumer.subscribe([args.topic])

    stopping = False

    def _stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _stop)

    print(f"Listening on {args.topic} (Ctrl+C to stop)...")
    count = 0
    try:
        while not stopping:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(msg.error(), file=sys.stderr)
                continue
            count += 1
            payload = json.loads(msg.value().decode("utf-8"))
            tel = payload.get("telemetry", {})
            print(
                f"#{count} partition={msg.partition()} key={msg.key().decode() if msg.key() else '-'} "
                f"type={payload.get('event_type')} engine={tel.get('unique_engine_id')} "
                f"cycle={tel.get('cycle')} RUL={tel.get('RUL')}"
            )
    finally:
        consumer.close()
        print(f"Consumed {count} messages.")


if __name__ == "__main__":
    main()
