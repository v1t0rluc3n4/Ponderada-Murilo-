"""Prepara um recorte fixo do CSV diário da Bitstamp/CryptoDataDownload."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, help="CSV original já baixado; se omitido, baixa da fonte")
    args = parser.parse_args()
    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    source_path = args.source or raw_dir / "Bitstamp_BTCUSD_d.csv"
    if args.source is None:
        with urlopen(SOURCE, timeout=60) as response:
            source_path.write_bytes(response.read())

    # A primeira linha do arquivo é um link, não o cabeçalho das colunas.
    raw = pd.read_csv(source_path, skiprows=1)
    data = raw[["date", "close"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    invalid = data["date"].isna() | data["close"].isna() | (data["close"] <= 0)
    invalid_count = int(invalid.sum())
    data = data.loc[~invalid].copy()
    data = data.loc[data["date"].between("2023-01-01", "2025-12-31")]
    duplicate_count = int(data["date"].duplicated().sum())
    if duplicate_count:
        raise ValueError("Há datas duplicadas no recorte. Verifique a fonte antes de continuar.")
    data = data.sort_values("date").reset_index(drop=True)
    expected = pd.date_range("2023-01-01", "2025-12-31", freq="D")
    if not pd.DatetimeIndex(data["date"]).equals(expected):
        raise ValueError("O recorte não possui todos os dias de 2023 a 2025.")
    output = ROOT / "data" / "btc_daily.csv"
    data.to_csv(output, index=False, date_format="%Y-%m-%d", lineterminator="\n")
    provenance = {
        "source_url": SOURCE,
        "exchange": "Bitstamp",
        "symbol": "BTC/USD",
        "frequency": "daily",
        "date_convention": "Data UTC de abertura do candle diário; close é o fechamento desse candle.",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(raw),
        "invalid_rows_in_source": invalid_count,
        "duplicate_dates_in_period": duplicate_count,
        "rows": len(data),
        "start": "2023-01-01",
        "end": "2025-12-31",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (ROOT / "data" / "source.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(provenance, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
