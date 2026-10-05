import hashlib
import json
import logging
import math
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from features import FEATURES, WINDOW, make_input

logging.basicConfig(level=logging.INFO)
ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("ARTIFACT_DIR", ROOT / "artifacts"))


@asynccontextmanager
async def lifespan(app):
    model_path = ARTIFACTS / "model.joblib"
    metadata = json.loads((ARTIFACTS / "metadata.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != metadata["model_sha256"]:
        raise RuntimeError("O modelo não corresponde ao metadata.json. Execute o treinamento novamente.")
    if metadata["features"] != FEATURES or metadata["window"] != WINDOW:
        raise RuntimeError("A ordem de entrada do modelo é diferente da API.")
    app.state.model = joblib.load(model_path)
    app.state.metadata = metadata
    logging.info("Modelo carregado: %s; sha256=%s", model_path, digest)
    yield


app = FastAPI(title="Previsão de fechamento BTC/USD", lifespan=lifespan)
Price = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prices: list[Price] = Field(min_length=WINDOW, max_length=WINDOW, description="7 fechamentos diários consecutivos, do mais antigo ao mais recente")
    last_date: date = Field(description="Data UTC do último candle diário já fechado")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True, "model": app.state.metadata["model"]}


@app.post("/predict")
def predict(body: PredictionInput):
    if body.last_date >= date.max:
        raise HTTPException(status_code=422, detail="Data fora do intervalo para calcular o próximo dia.")
    value = float(app.state.model.predict(make_input(body.prices))[0])
    if not math.isfinite(value) or value <= 0:
        raise HTTPException(status_code=422, detail="O modelo retornou um preço inválido para essa entrada.")
    return {
        "symbol": "BTC-USD",
        "currency": "USD",
        "predicted_close": round(value, 2),
        "prediction_date": (body.last_date + timedelta(days=1)).isoformat(),
        "horizon_days": 1,
        "model": app.state.metadata["model"],
        "warning": "Previsão experimental. Não é recomendação de investimento.",
    }
