# GBM Treatment Optimization API v3.0

REST API для оптимизации лечения глиобластомы.  
Использует ансамблевую ML-модель (stacking) + симуляцию роста опухоли по модели Гомперца.

**Стек:** Python 3.12 · FastAPI · Uvicorn  
**Модель:** 115 признаков, R² > 99.4% по всем 4 параметрам

---

## Запуск

### Локально

Перед запуском скачать [архив](https://drive.google.com/file/d/1hvvvdLkFtKNuCw6LWm5ar7nnSlxJI8w7/view?usp=drive_link) и распаковать в `vivida/`.

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
# из папки vivida/
docker build -t gbm-api .
docker run -p 8080:8080 gbm-api
```

Сервер доступен на `http://localhost:8080`.  
Swagger UI: `http://localhost:8080/docs`

---

## Endpoints

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | Статус сервиса |
| GET | `/model/info` | Информация о модели и признаках |
| POST | `/optimize` | Полные результаты grid-search оптимизации |
| POST | `/optimize/summary` | Краткое резюме для UI |
| POST | `/validate` | Валидация данных пациента |

---

## Входные данные

**Обязательные поля:**

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | ID пациента |
| `age` | float | Возраст (0–120) |
| `tumor_size_before` | float | Размер опухоли до лечения (см³, > 0) |
| `kps` | float | Шкала Карновского (0–100) |
| `treatment` | string | Тип лечения: `chemoradiotherapy`, `chemotherapy`, `radiation` |

**Дозировки (опционально):**

```json
"chemotherapy": { "drug": "Temozolomide", "dose_mg_per_m2": 75, "cycles": 6 },
"radiotherapy":  { "total_dose_Gy": 60, "fractions": 30 }
```

**Генетические маркеры (опционально):**  
`mgmt_methylation`, `idh_mutation`, `egfr_amplification`, `tert_mutation`, `atrx_mutation` — boolean

**Клинические признаки (опционально):**  
`edema_volume` (см³), `steroid_dose` (мг), `antiseizure_meds` — boolean

**Неврологические симптомы (опционально):**  
`neurological_symptoms` (строка: `"headache, seizures"`) или флаги:  
`has_headache`, `has_seizures`, `has_motor_deficit`, `has_sensory_deficit`,  
`has_cognitive_decline`, `has_speech_disturbance`, `has_visual_disturbance`

**Прочее (опционально):**  
`gender`, `resection_extent`, `molecular_subtype`, `tumor_location`,  
`contrast_enhancement`, `stage`, `lateralization`, `rano_response`,  
`family_history`, `previous_radiation`

Полный пример: [`example_patient.json`](vivida/example_patient.json)

---

## Пример запроса

```bash
curl -X POST http://localhost:8080/optimize/summary \
  -H "Content-Type: application/json" \
  -d @example_patient.json
```

**Ответ:**

```json
{
  "model_version": "3.0",
  "patient_id": "PATIENT_001",
  "doctor_plan": {
    "treatment_type": "chemoradiotherapy",
    "prediction": 1.36
  },
  "global_optimal": {
    "treatment_type": "chemoradiotherapy",
    "prediction": 1.21,
    "improvement_percent": 11.0,
    "chemotherapy": { "dose_mg_per_m2": 150 },
    "radiotherapy": { "total_dose_Gy": 66, "fractions": 33, "BED": 79.2 }
  },
  "local_optimal": {
    "treatment_type": "chemoradiotherapy",
    "prediction": 1.21,
    "improvement_percent": 11.0
  },
  "recommendation": "major_change"
}
```

`recommendation`: `optimal` | `minor_change` (≥3%) | `major_change` (≥10%)

---

## Модель

### Алгоритм

1. Построение вектора из 115 признаков (числовые + one-hot + взаимодействия + нелинейные члены)
2. Нормализация (StandardScaler)
3. Stacking ensemble: XGBoost + GBM + RandomForest + ExtraTrees + MLP → мета-слой Ridge
4. Предсказание 4 параметров модели Гомперца: `r`, `K`, `α`, `β`
5. Численная симуляция роста опухоли на 12 месяцев
6. Grid search по дозировкам — глобальная и локальная оптимизация

### Уравнение роста (Гомперц)

```
dV/dt = r·V·ln(K/V) − α·(chemo)·V − β·(radio)·V
```

### Точность модели

| Параметр | R² |
|---|---|
| r (скорость роста) | 99.98% |
| K (предельный объём) | 99.99% |
| α (чувств. к химио) | 99.93% |
| β (чувств. к радио) | 99.48% |

Обучено на 4 961 пациенте.

---

## Структура проекта

```
vivida/
├── main.py                                       # FastAPI приложение
├── optimizer.py                                  # ML логика и симуляция
├── requirements.txt
├── Dockerfile
├── example_patient.json
└── gbm_models_output_all90_dosage_full_features/ # Обученные модели
    ├── stacked_models.joblib
    ├── onehot_encoder.joblib
    ├── scaler.joblib
    ├── feature_columns.json
    └── metadata.json
```
