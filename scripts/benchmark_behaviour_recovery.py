#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nimo.application.container import ApplicationContainer

LABELS = ("periodic", "distributional", "spontaneous")


def _latest_truth(user_root: Path) -> dict[str, Any]:
    paths = sorted(user_root.glob("synthetic/run_*/ground_truth.json"))
    if not paths:
        raise FileNotFoundError(f"No synthetic ground truth found below {user_root / 'synthetic'}")
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def _truth_by_category(payload: dict[str, Any]) -> dict[str, set[str]]:
    truth: dict[str, set[str]] = defaultdict(set)
    for row in payload.get("transaction_truth", []):
        category = str(row.get("category_truth") or "uncategorised")
        raw = row.get("behaviours_truth", "[]")
        labels = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        truth[category].update(label for label in labels if label in LABELS)
    return dict(truth)


def evaluate(user: str, *, project_root: Path, data_root: Path | None, threshold: float) -> dict[str, Any]:
    app = ApplicationContainer.for_user(user, project_root=project_root, data_root=data_root)
    inferred = app.behaviours.refresh(force=True).get("categories", {})
    truth = _truth_by_category(_latest_truth(app.workspace.root))
    rows: list[dict[str, Any]] = []
    confusion = {label: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for label in LABELS}
    categories = sorted(set(truth) | set(inferred))
    for category in categories:
        true_labels = truth.get(category, set())
        payload = inferred.get(category, {})
        scores = {
            "periodic": float(payload.get("periodic", {}).get("score", 0.0)),
            "distributional": float(payload.get("distributional", {}).get("distributional_score", 0.0)),
            "spontaneous": float(payload.get("spontaneous", {}).get("score", 0.0)),
        }
        predicted = {label for label, score in scores.items() if score >= threshold}
        rows.append(
            {
                "category": category,
                "truth": sorted(true_labels),
                "predicted": sorted(predicted),
                "scores": scores,
            }
        )
        for label in LABELS:
            actual, guess = label in true_labels, label in predicted
            key = "tp" if actual and guess else "fn" if actual else "fp" if guess else "tn"
            confusion[label][key] += 1
    metrics: dict[str, Any] = {}
    for label, counts in confusion.items():
        precision = counts["tp"] / max(1, counts["tp"] + counts["fp"])
        recall = counts["tp"] / max(1, counts["tp"] + counts["fn"])
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        metrics[label] = {**counts, "precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6)}
    return {
        "user": user,
        "threshold": threshold,
        "category_count": len(categories),
        "metrics": metrics,
        "rows": rows,
        "note": "Ground truth is read only by this benchmark; the inference service receives normalized transactions only.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare inferred behaviour labels with synthetic ground truth")
    parser.add_argument("user", nargs="?", default="sample_user")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.user, project_root=args.project_root.resolve(), data_root=args.data_root, threshold=args.threshold)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
