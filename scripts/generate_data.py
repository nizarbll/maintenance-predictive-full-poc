import argparse
import csv
import math
import random
from pathlib import Path
from typing import Dict, List

SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22) if i != 16]
OP_COLS = [f"op_setting_{i}" for i in range(1, 4)]
DEFAULT_ENGINE_TYPES = ["A", "B", "C"]


def normal_noise(scale: float) -> float:
    return random.gauss(0.0, scale)


def build_engine_row(unit_number: int, cycle: int, engine_type: str, base_values: Dict[str, float]) -> Dict[str, float]:
    row = {
        "unit_number": unit_number,
        "cycle": cycle,
        "engine_type": engine_type,
        "unique_engine_id": f"ENG_{unit_number:03d}"
    }

    # Operational settings vary slowly over time
    row["op_setting_1"] = max(0.0, base_values["op1"] + 0.001 * cycle + normal_noise(0.02))
    row["op_setting_2"] = max(0.0, base_values["op2"] + 0.002 * math.sin(cycle / 15.0) + normal_noise(0.03))
    row["op_setting_3"] = max(0.0, base_values["op3"] + 0.0015 * math.cos(cycle / 25.0) + normal_noise(0.02))

    for sensor in SENSOR_COLS:
        drift = base_values["drift"] * cycle
        noise = normal_noise(base_values["noise"])
        scale = base_values["scale"]
        row[sensor] = float(max(0.0, base_values[sensor] + drift + noise) * scale)

    return row


def create_dataset(
    engines: int,
    min_cycles: int,
    max_cycles: int,
    engine_types: List[str],
    seed: int,
) -> List[Dict[str, float]]:
    random.seed(seed)

    rows: List[Dict[str, float]] = []
    for unit_number in range(1, engines + 1):
        engine_type = engine_types[(unit_number - 1) % len(engine_types)]
        cycle_count = random.randint(min_cycles, max_cycles)

        base_values = {
            "op1": random.uniform(0.75, 1.25),
            "op2": random.uniform(0.1, 0.8),
            "op3": random.uniform(0.5, 1.2),
            "drift": random.uniform(0.0004, 0.0012),
            "noise": random.uniform(0.01, 0.05),
            "scale": random.uniform(0.85, 1.15),
        }

        for sensor in SENSOR_COLS:
            base_values[sensor] = random.uniform(0.05, 0.95)

        for cycle in range(1, cycle_count + 1):
            row = build_engine_row(unit_number, cycle, engine_type, base_values)
            row["RUL"] = cycle_count - cycle
            rows.append(row)

    return rows


def write_dataset(rows: List[Dict[str, float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    column_order = ["unit_number", "cycle", "RUL"] + OP_COLS + SENSOR_COLS + ["engine_type", "unique_engine_id"]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_order)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic NASA turbofan merged dataset for Kafka ingestion."
    )
    parser.add_argument("--engines", type=int, default=20, help="Number of engine units to simulate.")
    parser.add_argument("--min-cycles", type=int, default=50, help="Minimum cycles per engine.")
    parser.add_argument("--max-cycles", type=int, default=180, help="Maximum cycles per engine.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dataset") / "merged_dataset.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data generation.",
    )
    parser.add_argument(
        "--engine-types",
        type=str,
        default=",".join(DEFAULT_ENGINE_TYPES),
        help="Comma-separated list of engine types.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine_types = [t.strip() for t in args.engine_types.split(",") if t.strip()]
    df = create_dataset(
        engines=args.engines,
        min_cycles=args.min_cycles,
        max_cycles=args.max_cycles,
        engine_types=engine_types,
        seed=args.seed,
    )

    write_dataset(df, args.output)
    print(
        f"Generated {len(df):,} rows for {args.engines} engines and saved to {args.output.resolve()}"
    )


if __name__ == "__main__":
    main()
