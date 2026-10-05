FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY features.py .
COPY training ./training
COPY data/btc_daily.csv ./data/btc_daily.csv
CMD ["python", "-m", "training.train"]
