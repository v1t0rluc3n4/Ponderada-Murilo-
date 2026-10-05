"""Verifica o backend de verdade por HTTP, inclusive depois de reiniciar."""

import argparse
import csv
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def call(url, body=None):
    request = Request(url, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    with (ROOT / "data/btc_daily.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))[-7:]
    valid = {"prices": [float(row["close"]) for row in rows], "last_date": rows[-1]["date"]}
    code, body = call(args.url + "/health")
    assert code == 200 and body["model_loaded"] is True, (code, body)
    print("GET /health: HTTP 200; modelo carregado")
    code, body = call(args.url + "/predict", valid)
    assert code == 200 and body["prediction_date"] == "2026-01-01", (code, body)
    assert body["predicted_close"] > 0, body
    print("POST /predict:", json.dumps(body, ensure_ascii=False))
    for prices in [valid["prices"][:6], [-1] + valid["prices"][1:]]:
        code, body = call(args.url + "/predict", {**valid, "prices": prices})
        assert code == 422, (code, body)
        print("POST /predict com entrada inválida: HTTP 422")
    print("Teste HTTP concluído sem falhas.")


if __name__ == "__main__":
    main()
