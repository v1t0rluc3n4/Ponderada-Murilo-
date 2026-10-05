"""Treina uma regressão linear e compara com repetir o último fechamento."""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from features import FEATURES, WINDOW, make_examples

ROOT = Path(__file__).resolve().parents[1]


def metrics(actual, predicted):
    return {
        "mae_usd": float(mean_absolute_error(actual, predicted)),
        "rmse_usd": float(root_mean_squared_error(actual, predicted)),
    }


def main():
    csv_path = ROOT / "data" / "btc_daily.csv"
    data = pd.read_csv(csv_path, parse_dates=["date"])
    if list(data.columns) != ["date", "close"]:
        raise ValueError("O CSV precisa ter as colunas date e close, nessa ordem.")
    if data["date"].isna().any() or data["date"].duplicated().any():
        raise ValueError("Datas inválidas ou duplicadas.")
    if not data["date"].is_monotonic_increasing:
        raise ValueError("As datas precisam estar em ordem crescente.")
    if not data["date"].diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("Faltam dias na série. O horizonte deve ser de um dia.")
    if not np.isfinite(data["close"]).all() or (data["close"] <= 0).any():
        raise ValueError("Preços devem ser positivos e finitos.")

    examples = make_examples(data)
    split = int(len(examples) * 0.8)
    if split < 10 or len(examples) - split < 2:
        raise ValueError("Dados insuficientes para treinar e avaliar.")
    train = examples.iloc[:split]
    test = examples.iloc[split:]
    model = LinearRegression()
    model.fit(train[FEATURES], train["target"])
    prediction = model.predict(test[FEATURES])
    baseline = test["close_lag_0"].to_numpy()
    results = {
        "linear_regression": metrics(test["target"], prediction),
        "last_close_baseline": metrics(test["target"], baseline),
        "train_examples": len(train),
        "test_examples": len(test),
    }
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    joblib.dump(model, output / "model.joblib")
    reloaded = joblib.load(output / "model.joblib")
    np.testing.assert_allclose(reloaded.predict(test[FEATURES]), prediction)
    metadata = {
        "model": "LinearRegression",
        "symbol": "BTC-USD",
        "currency": "USD",
        "window": WINDOW,
        "horizon_days": 1,
        "input_order": "oldest_to_newest",
        "features": FEATURES,
        "data_start": data["date"].iloc[0].date().isoformat(),
        "data_end": data["date"].iloc[-1].date().isoformat(),
        "train_target_start": train["target_date"].iloc[0].date().isoformat(),
        "train_target_end": train["target_date"].iloc[-1].date().isoformat(),
        "test_target_start": test["target_date"].iloc[0].date().isoformat(),
        "test_target_end": test["target_date"].iloc[-1].date().isoformat(),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256((output / "model.joblib").read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "joblib_version": joblib.__version__,
        "refit_on_all_data": False,
    }
    for name, content in [("metrics.json", results), ("metadata.json", metadata)]:
        (output / name).write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame({
        "date": test["target_date"].dt.strftime("%Y-%m-%d"),
        "actual_close": test["target"],
        "predicted_close": prediction,
        "baseline_close": baseline,
    }).to_csv(output / "test_predictions.csv", index=False, lineterminator="\n")
    print(f"CSV: {len(data)} dias; exemplos completos: {len(examples)}")
    print(json.dumps(results, indent=2))
    print(f"Alvos de treino: {metadata['train_target_start']} a {metadata['train_target_end']}")
    print(f"Alvos de teste: {metadata['test_target_start']} a {metadata['test_target_end']}")
    print("Modelo exportado e recarregado com as mesmas previsões.")


if __name__ == "__main__":
    main()
