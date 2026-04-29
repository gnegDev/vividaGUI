FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py optimizer.py ./
COPY gbm_models_output_all90_dosage_full_features/ ./gbm_models_output_all90_dosage_full_features/

EXPOSE 8080

CMD ["uvicorn", "main:app", "--log-level", "debug", "--host", "0.0.0.0", "--port", "8080"]
