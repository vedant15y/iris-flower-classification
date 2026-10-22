"""Train and use a small, dependency-free Iris k-nearest-neighbors classifier."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


FEATURES = ("SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm")
SEED = 42


def parse_measurement(value: str) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def load_data(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not set(FEATURES + ("Species",)).issubset(reader.fieldnames or []):
            raise ValueError("CSV needs the four Iris measurement columns and Species")
        rows = list(reader)
    data = []
    counts = Counter()
    for row in rows:
        label = (row["Species"] or "").strip()
        values = [parse_measurement(row[name]) for name in FEATURES]
        if not label:
            counts["unlabeled"] += 1
        elif all(value is None for value in values):
            counts["all_features_missing"] += 1
        else:
            data.append((values, label))
        counts["invalid_or_missing_measurements"] += sum(value is None for value in values)
    return data, dict(counts)


def stratified_split(data, test_fraction=0.2, seed=SEED):
    groups = defaultdict(list)
    for row in data:
        groups[row[1]].append(row)
    if len(groups) < 2 or any(len(group) < 6 for group in groups.values()):
        raise ValueError("Need at least two classes with six labeled rows each")
    rng = random.Random(seed)
    train, test = [], []
    for label in sorted(groups):
        group = groups[label][:]
        rng.shuffle(group)
        n_test = max(1, round(len(group) * test_fraction))
        test.extend(group[:n_test])
        train.extend(group[n_test:])
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def fit_preprocessing(rows):
    columns = list(zip(*(values for values, _ in rows)))
    medians = [statistics.median(v for v in col if v is not None) for col in columns]
    filled = [[medians[i] if value is None else value for i, value in enumerate(values)]
              for values, _ in rows]
    means = [statistics.mean(col) for col in zip(*filled)]
    scales = [statistics.pstdev(col) or 1.0 for col in zip(*filled)]
    return medians, means, scales


def transform(values, medians, means, scales):
    return [(float(medians[i] if value is None else value) - means[i]) / scales[i]
            for i, value in enumerate(values)]


def fit(rows, k):
    medians, means, scales = fit_preprocessing(rows)
    return {
        "features": list(FEATURES), "k": k,
        "medians": medians, "means": means, "scales": scales,
        "samples": [{"x": transform(values, medians, means, scales), "label": label}
                    for values, label in rows],
    }


def predict(model, values):
    if len(values) != len(FEATURES):
        raise ValueError("Exactly four measurements are required")
    x = transform(values, model["medians"], model["means"], model["scales"])
    distances = sorted(
        (sum((a - b) ** 2 for a, b in zip(x, sample["x"])), sample["label"])
        for sample in model["samples"]
    )
    neighbors = distances[:model["k"]]
    votes = Counter(label for _, label in neighbors)
    # Distance sum resolves vote ties; label makes a final tie deterministic.
    winner = min(votes, key=lambda label: (-votes[label],
                                             sum(d for d, item in neighbors if item == label), label))
    return winner, votes[winner] / len(neighbors)


def select_k(train, folds=5):
    groups = defaultdict(list)
    for row in train:
        groups[row[1]].append(row)
    buckets = [[] for _ in range(folds)]
    for label in sorted(groups):
        rows = groups[label][:]
        random.Random(SEED).shuffle(rows)
        for i, row in enumerate(rows):
            buckets[i % folds].append(row)
    scores = {}
    for k in (1, 3, 5, 7, 9):
        correct = total = 0
        for i in range(folds):
            training = [row for j, bucket in enumerate(buckets) if j != i for row in bucket]
            model = fit(training, k)
            for values, label in buckets[i]:
                correct += predict(model, values)[0] == label
                total += 1
        scores[str(k)] = correct / total
    best = min((int(k) for k in scores), key=lambda k: (-scores[str(k)], k))
    return best, scores


def evaluate(model, test):
    labels = sorted({label for _, label in test})
    matrix = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    for values, actual in test:
        predicted, _ = predict(model, values)
        matrix[actual][predicted] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": sum(matrix[label].values())}
    return {"accuracy": sum(matrix[label][label] for label in labels) / len(test),
            "macro_f1": statistics.mean(item["f1"] for item in per_class.values()),
            "per_class": per_class, "confusion_matrix": matrix}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train_cmd = commands.add_parser("train", help="train, tune, and evaluate")
    train_cmd.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "Iris_data_sample.csv")
    train_cmd.add_argument("--model", type=Path, default=Path(__file__).parent / "model.json")
    train_cmd.add_argument("--metrics", type=Path, default=Path(__file__).parent / "metrics.json")
    predict_cmd = commands.add_parser("predict", help="predict from four centimeter measurements")
    predict_cmd.add_argument("measurements", nargs=4, type=float, metavar="CM")
    predict_cmd.add_argument("--model", type=Path, default=Path(__file__).parent / "model.json")
    args = parser.parse_args()
    if args.command == "train":
        data, cleaning = load_data(args.data)
        training, test = stratified_split(data)
        k, cv = select_k(training)
        model = fit(training, k)
        report = {"seed": SEED, "training_rows": len(training), "test_rows": len(test),
                  "cleaning": cleaning, "selected_k": k, "cross_validation_accuracy": cv,
                  "test": evaluate(model, test)}
        args.model.write_text(json.dumps(model, indent=2), encoding="utf-8")
        args.metrics.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Training: {len(training)} rows; test: {len(test)} rows; k={k}")
        print(f"Test accuracy: {report['test']['accuracy']:.3f}; macro F1: {report['test']['macro_f1']:.3f}")
        print(f"Saved {args.model} and {args.metrics}")
    else:
        if any(not math.isfinite(v) or v <= 0 for v in args.measurements):
            parser.error("measurements must be positive, finite numbers")
        model = json.loads(args.model.read_text(encoding="utf-8"))
        label, vote_share = predict(model, args.measurements)
        print(f"{label} (neighbor vote share: {vote_share:.0%})")


if __name__ == "__main__":
    main()
