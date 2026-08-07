"""Analyse generated seeded CSV bank statements."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import matplotlib.pyplot as plt
import pandas as pd

from utils import (
    canonical_amount_series,
    find_field_name,
    flatten_nested_strings,
    load_csv,
    load_yaml_mapping,
    normalise_text_aggressive,
)

GEN_ANALYSIS_VERSION = "2.0.0"


def _analysis_config(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    value = policy.get("analysis", {})
    return value if isinstance(value, Mapping) else {}


def _configured_transaction_types(policy: Mapping[str, Any]) -> list[str]:
    groups = policy.get("transaction_types", {})
    if not isinstance(groups, Mapping):
        return []
    return flatten_nested_strings(groups.values())


def _constant_field_results(
    frame: pd.DataFrame,
    policy: Mapping[str, Any],
) -> pd.DataFrame:
    configured = _analysis_config(policy).get("constant_fields", [])
    rows: list[dict[str, Any]] = []
    for canonical in configured:
        actual = find_field_name(policy, str(canonical), frame.columns)
        if actual is None:
            rows.append({
                "field": canonical,
                "column": None,
                "present": False,
                "unique_non_null": 0,
                "constant": None,
                "value": None,
            })
            continue
        unique_values = frame[actual].dropna().unique().tolist()
        rows.append({
            "field": canonical,
            "column": actual,
            "present": True,
            "unique_non_null": len(unique_values),
            "constant": len(unique_values) <= 1,
            "value": unique_values[0] if len(unique_values) == 1 else None,
        })
    return pd.DataFrame(rows)


def _transaction_type_counts(
    frame: pd.DataFrame,
    policy: Mapping[str, Any],
) -> pd.Series | None:
    actual = find_field_name(policy, "transaction_type", frame.columns)
    if actual is None:
        return None

    configured = _configured_transaction_types(policy)
    observed = frame[actual].astype("string").fillna("<MISSING>")
    counts = observed.value_counts(dropna=False)

    # Include every configured code, even when absent, then append unexpected codes.
    configured_index = pd.Index(configured, dtype="object")
    unexpected = [value for value in counts.index.tolist() if value not in configured]
    full_index = configured_index.append(pd.Index(unexpected, dtype="object"))
    return counts.reindex(full_index, fill_value=0).astype(int)


def _save_or_show(fig: plt.Figure, output: Path | None, show: bool) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, bbox_inches="tight")
    if show:
        fig.show()
    else:
        plt.close(fig)


def analyse_statement_df(
    frame: pd.DataFrame,
    policy: Mapping[str, Any],
    *,
    source_name: str = "statement",
    plot_dir: Path | None = None,
    show_plots: bool | None = None,
    print_report: bool = True,
) -> dict[str, Any]:
    """Validate and analyse one statement DataFrame."""
    cfg = _analysis_config(policy)
    if show_plots is None:
        show_plots = bool(cfg.get("show_plots", True))

    date_col = find_field_name(policy, "date", frame.columns)
    if date_col is None:
        raise KeyError("No configured date alias was found in the statement")

    dates = pd.to_datetime(frame[date_col], errors="coerce")
    amounts = canonical_amount_series(frame, policy)
    valid = dates.notna() & amounts.notna()
    analysis_frame = pd.DataFrame({"date": dates[valid], "amount": amounts[valid]}).sort_values("date")
    if analysis_frame.empty:
        raise ValueError("No rows contain both a valid date and a valid amount")

    constant_results = _constant_field_results(frame, policy)
    type_counts = _transaction_type_counts(frame, policy)

    date_counts = analysis_frame["date"].dt.normalize().value_counts().sort_index()
    amount_summary = analysis_frame["amount"].describe().round(2)
    date_summary = {
        "minimum": analysis_frame["date"].min(),
        "maximum": analysis_frame["date"].max(),
        "span_days": int((analysis_frame["date"].max() - analysis_frame["date"].min()).days),
        "unique_dates": int(analysis_frame["date"].dt.normalize().nunique()),
        "rows": int(len(analysis_frame)),
    }

    running_col = find_field_name(policy, "running_balance", frame.columns)
    if running_col:
        running_balance = pd.Series(
            pd.to_numeric(frame.loc[valid, running_col], errors="coerce").to_numpy(),
            index=analysis_frame.index,
        )
        if running_balance.isna().any():
            running_balance = analysis_frame["amount"].cumsum()
            balance_source = "calculated because configured balance was not fully numeric"
        else:
            balance_source = running_col
    else:
        running_balance = analysis_frame["amount"].cumsum()
        balance_source = "calculated from amount"
    analysis_frame["balance"] = running_balance.to_numpy()

    if print_report:
        print(f"\nAnalysis: {source_name}")
        print(f"Rows analysed: {len(analysis_frame)}")
        print(
            "Date range: "
            f"{date_summary['minimum'].date()} to {date_summary['maximum'].date()} "
            f"({date_summary['span_days']} days, {date_summary['unique_dates']} unique dates)"
        )
        print("\nAmount distribution:")
        print(amount_summary.to_string())

        if not constant_results.empty:
            print("\nConstant-field validation:")
            print(constant_results.to_string(index=False))
            failed = constant_results[
                constant_results["present"] & (constant_results["constant"] == False)  # noqa: E712
            ]
            if not failed.empty:
                print("WARNING: Expected constant fields changed within the statement.")

        if type_counts is not None:
            print("\nTransaction-type counts (configured zero-count values included):")
            print(type_counts.to_string())
        else:
            print("\nTransaction type: column not present.")

        print(f"\nBalance source: {balance_source}")

    bins = int(cfg.get("amount_histogram_bins", 20))
    date_frequency = str(cfg.get("date_frequency", "D"))
    file_format = str(cfg.get("plot_format", "png"))
    safe_source = normalise_text_aggressive(Path(source_name).stem) or "statement"

    amount_fig, amount_ax = plt.subplots()
    amount_ax.hist(analysis_frame["amount"], bins=bins)
    amount_ax.set_title("Amount distribution")
    amount_ax.set_xlabel("Amount")
    amount_ax.set_ylabel("Frequency")
    _save_or_show(
        amount_fig,
        None if plot_dir is None else plot_dir / f"{safe_source}_amount_distribution.{file_format}",
        show_plots,
    )

    grouped_dates = analysis_frame.set_index("date").resample(date_frequency).size()
    date_fig, date_ax = plt.subplots()
    date_ax.plot(grouped_dates.index, grouped_dates.values)
    date_ax.set_title(f"Transaction dates by {date_frequency}")
    date_ax.set_xlabel("Date")
    date_ax.set_ylabel("Transaction count")
    date_fig.autofmt_xdate()
    _save_or_show(
        date_fig,
        None if plot_dir is None else plot_dir / f"{safe_source}_date_distribution.{file_format}",
        show_plots,
    )

    balance_fig, balance_ax = plt.subplots()
    balance_ax.plot(analysis_frame["date"], analysis_frame["balance"])
    balance_ax.set_title("Balance over time")
    balance_ax.set_xlabel("Date")
    balance_ax.set_ylabel("Balance")
    balance_fig.autofmt_xdate()
    _save_or_show(
        balance_fig,
        None if plot_dir is None else plot_dir / f"{safe_source}_balance_over_time.{file_format}",
        show_plots,
    )

    return {
        "date_summary": date_summary,
        "amount_summary": amount_summary,
        "constant_fields": constant_results,
        "transaction_type_counts": type_counts,
        "balance_source": balance_source,
    }


def analyse_statement_file(
    statement_path: Path,
    policy_path: Path,
    *,
    plot_dir: Path | None = None,
    show_plots: bool | None = None,
) -> dict[str, Any]:
    policy = load_yaml_mapping(policy_path)
    frame = load_csv(statement_path)
    return analyse_statement_df(
        frame,
        policy,
        source_name=statement_path.name,
        plot_dir=plot_dir,
        show_plots=show_plots,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyse a generated CSV bank statement")
    parser.add_argument("path", type=Path, help="CSV statement to analyse")
    parser.add_argument("-c", "--config", type=Path, default=Path("generator_policy.yaml"))
    parser.add_argument("-o", "--plot-dir", type=Path, default=None)
    parser.add_argument("--no-show", action="store_true", help="Do not open plot windows")
    parser.add_argument("--version", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"Generator analysis version\t{GEN_ANALYSIS_VERSION}")
        return 0
    try:
        analyse_statement_file(
            args.path,
            args.config,
            plot_dir=args.plot_dir,
            show_plots=False if args.no_show else None,
        )
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"Analysis error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())