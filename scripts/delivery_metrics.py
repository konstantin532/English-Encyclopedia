#!/usr/bin/env python3
"""Метрики поставки: скорость CI и частота выкладок по истории GitHub Actions.

    GITHUB_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/delivery_metrics.py --days 30 --output metrics.md

Считает по завершённым запускам за период:
- CI на PR: медиана и 90-й процентиль времени до результата, доля успешных;
- выкладки (workflow «Deploy to VPS»): сколько успешных и в среднем за неделю.
Только чтение API; токену достаточно права actions: read.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

API = "https://api.github.com"


@dataclass(frozen=True)
class Run:
    conclusion: str | None
    event: str
    started: datetime
    finished: datetime

    @property
    def minutes(self) -> float:
        return (self.finished - self.started).total_seconds() / 60


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_runs(payload: dict) -> list[Run]:
    runs = []
    for item in payload.get("workflow_runs", []):
        if item.get("status") != "completed" or not item.get("run_started_at"):
            continue
        runs.append(
            Run(
                conclusion=item.get("conclusion"),
                event=item.get("event", ""),
                started=_parse_time(item["run_started_at"]),
                finished=_parse_time(item["updated_at"]),
            )
        )
    return runs


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))
    return ordered[index]


def summarize(ci: list[Run], deploys: list[Run], days: int) -> dict:
    finished = [run for run in ci if run.event == "pull_request" and run.conclusion in {"success", "failure"}]
    durations = [run.minutes for run in finished]
    shipped = [run for run in deploys if run.conclusion == "success"]
    return {
        "days": days,
        "ci_runs": len(finished),
        "ci_median_minutes": round(statistics.median(durations), 1) if durations else None,
        "ci_p90_minutes": round(percentile(durations, 0.9), 1) if durations else None,
        "ci_success_rate": round(sum(r.conclusion == "success" for r in finished) / len(finished), 3)
        if finished
        else None,
        "deploys": len(shipped),
        "deploys_per_week": round(len(shipped) / (days / 7), 2),
    }


def render(summary: dict) -> str:
    def show(value, suffix=""):
        return "нет данных" if value is None else f"{value}{suffix}"

    rate = summary["ci_success_rate"]
    return "\n".join(
        [
            f"# Метрики поставки за {summary['days']} дней",
            "",
            "| Метрика | Значение |",
            "|---|---|",
            f"| Запусков CI на PR | {summary['ci_runs']} |",
            f"| CI, медиана | {show(summary['ci_median_minutes'], ' мин')} |",
            f"| CI, 90-й процентиль | {show(summary['ci_p90_minutes'], ' мин')} |",
            f"| CI, успешных | {show(None if rate is None else round(rate * 100), '%')} |",
            f"| Успешных выкладок | {summary['deploys']} |",
            f"| Выкладок в неделю | {summary['deploys_per_week']} |",
            "",
        ]
    )


def fetch(repo: str, workflow: str, since: datetime, token: str) -> list[Run]:
    runs: list[Run] = []
    for page in range(1, 11):
        url = (
            f"{API}/repos/{repo}/actions/workflows/{workflow}/runs"
            f"?per_page=100&page={page}&created=%3E%3D{since.date().isoformat()}"
        )
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 — только api.github.com
            payload = json.load(response)
        batch = parse_runs(payload)
        runs += batch
        if len(payload.get("workflow_runs", [])) < 100:
            break
    return runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output")
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    since = datetime.now(UTC) - timedelta(days=args.days)
    summary = summarize(fetch(repo, "ci.yml", since, token), fetch(repo, "deploy-vps.yml", since, token), args.days)
    report = render(summary)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
