import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import pandas as pd
from fastapi.testclient import TestClient

from backend import app as api
from features import FEATURES, make_examples, make_input

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_window_uses_only_past_and_current_prices(self):
        data = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=10), "close": range(1, 11)})
        examples = make_examples(data)
        self.assertEqual(examples.iloc[0][FEATURES].tolist(), list(range(1, 8)))
        self.assertEqual(examples.iloc[0]["target"], 8)
        self.assertEqual(len(examples), 3)
        self.assertEqual(examples.iloc[0]["target_date"], pd.Timestamp("2025-01-08"))

    def test_saved_training_and_test_targets_do_not_overlap(self):
        metadata = json.loads((ROOT / "artifacts/metadata.json").read_text(encoding="utf-8"))
        self.assertLess(metadata["train_target_end"], metadata["test_target_start"])
        self.assertEqual(metadata["features"], FEATURES)
        digest = hashlib.sha256((ROOT / "data/btc_daily.csv").read_bytes()).hexdigest()
        self.assertEqual(metadata["csv_sha256"], digest)

    def test_prediction_really_comes_from_saved_model(self):
        data = pd.read_csv(ROOT / "data/btc_daily.csv").tail(7)
        prices = data["close"].tolist()
        model = joblib.load(ROOT / "artifacts/model.joblib")
        expected = round(float(model.predict(make_input(prices))[0]), 2)
        with TestClient(api.app) as client:
            self.assertEqual(client.get("/health").json()["model_loaded"], True)
            response = client.post("/predict", json={"prices": prices, "last_date": "2025-12-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["predicted_close"], expected)
        self.assertEqual(response.json()["prediction_date"], "2026-01-01")

    def test_bad_inputs_are_rejected(self):
        valid = {"prices": [60000] * 7, "last_date": "2025-12-31"}
        bad_inputs = [
            {**valid, "prices": [60000] * 6},
            {**valid, "prices": [60000] * 8},
            {**valid, "prices": [-1] + [60000] * 6},
            {**valid, "prices": [0] + [60000] * 6},
            {**valid, "prices": ["abc"] + [60000] * 6},
            {**valid, "last_date": "data errada"},
            {**valid, "last_date": "9999-12-31"},
            {**valid, "extra": "campo desconhecido"},
            {"prices": [60000] * 7},
        ]
        with TestClient(api.app) as client:
            for body in bad_inputs:
                with self.subTest(body=body):
                    self.assertEqual(client.post("/predict", json=body).status_code, 422)
            # JSON com NaN não é válido; a validação numérica também rejeita strings não finitas.
            for value in ["NaN", "Infinity"]:
                self.assertEqual(client.post("/predict", json={**valid, "prices": [value] + [60000] * 6}).status_code, 422)

    def test_missing_artifact_prevents_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(api, "ARTIFACTS", Path(folder)):
                with self.assertRaises(FileNotFoundError):
                    with TestClient(api.app):
                        pass

    def test_wrong_model_hash_prevents_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            metadata = json.loads((ROOT / "artifacts/metadata.json").read_text(encoding="utf-8"))
            (path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (path / "model.joblib").write_bytes(b"arquivo diferente")
            with patch.object(api, "ARTIFACTS", path):
                with self.assertRaisesRegex(RuntimeError, "não corresponde"):
                    with TestClient(api.app):
                        pass


if __name__ == "__main__":
    unittest.main()
