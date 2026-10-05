"""Cliente sem dependências extras: lê 7 dias do CSV e faz uma chamada HTTP."""

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    with (ROOT / "data" / "btc_daily.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))[-7:]
    if len(rows) != 7:
        raise ValueError("O CSV deve ter pelo menos 7 dias.")
    dates = [date.fromisoformat(row["date"]) for row in rows]
    if any(b - a != timedelta(days=1) for a, b in zip(dates, dates[1:])):
        raise ValueError("Os 7 fechamentos não são de dias consecutivos.")
    payload = {"prices": [float(row["close"]) for row in rows], "last_date": rows[-1]["date"]}
    request = Request(args.url.rstrip("/") + "/predict", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    print("Entrada:")
    print(json.dumps(payload, indent=2))
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
            print(f"HTTP {response.status}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode()}") from error
    except URLError as error:
        raise SystemExit(f"Não foi possível acessar o backend: {error.reason}") from error


if __name__ == "__main__":
    main()
