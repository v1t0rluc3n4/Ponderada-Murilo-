"""A ordem dos preços precisa ser igual no treino e na API."""

import pandas as pd

WINDOW = 7
FEATURES = [f"close_lag_{lag}" for lag in range(WINDOW - 1, -1, -1)]


def make_examples(data):
    examples = pd.DataFrame(index=data.index)
    for lag, name in zip(range(WINDOW - 1, -1, -1), FEATURES):
        examples[name] = data["close"].shift(lag)
    examples["target"] = data["close"].shift(-1)
    examples["input_date"] = data["date"]
    examples["target_date"] = data["date"].shift(-1)
    return examples.dropna().reset_index(drop=True)


def make_input(prices):
    if len(prices) != WINDOW:
        raise ValueError("Informe exatamente 7 fechamentos, do mais antigo ao mais recente.")
    return pd.DataFrame([prices], columns=FEATURES)
