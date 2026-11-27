# E-SAG Phishing Classification Module (`esag/ml`)

Offline machine learning experiment and UI demonstration payload for **E-SAG (Endpoint Security & Access Guard)**.

## Dataset & Label Meanings

- **Source:** UCI Machine Learning Repository — *Website Phishing* (Dataset ID `379`, Neda Abdelhamid et al., `esag/ml/data/PhishingData.arff`).
- **Raw size:** `1,353` rows × `10` columns (`9` integer/categorical features + `Result` target, `0` missing values).
- **Features (9):** `SFH`, `popUpWidnow` *(spelled `popUpWidnow` in the ARFF header)*, `SSLfinal_State`, `Request_URL`, `URL_of_Anchor`, `web_traffic`, `URL_Length`, `age_of_domain`, `having_IP_Address`.
- **Target (`Result`) label meanings** (verified from UCI ID 379 metadata and raw class counts):

| Code | Meaning | Raw Rows (1,353) | Clean Rows (724) | Test Split (145) |
| ---: | :--- | ---: | ---: | ---: |
| `-1` | **Phishing** (*Phishy*) | 702 | 353 | 71 |
| `0` | **Suspicious** | 103 | 61 | 12 |
| `1` | **Legitimate** | 548 | 310 | 62 |

## Preprocessing & Experiment Setup

1. Load `PhishingData.arff` via `scipy.io.arff` and decode byte categorical values to integers.
2. Drop missing values (`0` found) and exact duplicate rows (`629` removed → `724` unique rows).
3. Perform an **80/20 stratified train/test split** (`random_state=42`): `579` training rows, `145` held-out test rows.
4. Train and evaluate four baseline classifiers (`GaussianNB`, `DecisionTreeClassifier`, `RandomForestClassifier`, `LogisticRegression`).

## Evaluation Results (Held-Out Test Set, 145 Rows)

Metrics below are weighted across the 3 classes (`["-1", "0", "1"]` in that confusion-matrix row/column order):

| Model | Accuracy | Weighted Precision | Weighted Recall | Weighted F1 |
| :--- | ---: | ---: | ---: | ---: |
| **Decision Tree** *(best)* | **0.8069** | **0.8081** | **0.8069** | **0.8054** |
| Random Forest | 0.8000 | 0.8062 | 0.8000 | 0.7951 |
| Naive Bayes | 0.7862 | 0.7907 | 0.7862 | 0.7751 |
| Logistic Regression | 0.7655 | 0.7860 | 0.7655 | 0.7418 |

Confusion matrix (`labels=["-1", "0", "1"]`) for **Decision Tree**:

```text
Actual \ Pred   -1 (Phish)   0 (Susp)   1 (Legit)
-1 (Phishing)           57          2          12
 0 (Suspicious)          2          7           3
 1 (Legitimate)          9          0          53
```

## Output Schema for the PySide6 UI (`esag/ml/ml_results.json`)

Running `train_eval.py` exports `esag/ml/ml_results.json` for the **"View ML demonstration"** tab:

- `label_meanings`: mapping `{"-1": "Phishing", "0": "Suspicious", "1": "Legitimate"}`.
- `best_model` & `models`: per-model metrics and `3x3` confusion matrices.
- `sample_examples`: `5` held-out test rows covering all three classes (`features`, `actual_label` / `actual_label_name`, `predicted_label` / `predicted_label_name`, and `predictions_by_model`).
- `limitations`: plain-language caveats to display in the UI.

## Limitations

- **Static historical features:** Uses 9 pre-extracted discrete indicators from the UCI Website Phishing dataset (ID 379, 2014/2016 release) rather than live URL or HTML feature extraction.
- **Duplicate removal impact:** `629` of `1,353` rows (`~46.5%`) were exact duplicates and removed, leaving `724` unique instances (`579` train / `145` test).
- **Class `0` ("Suspicious") imbalance:** Only `61` unique rows (`~8.4%` of clean data; `12` test rows), leading to lower recall/precision on borderline sites (e.g., Naive Bayes and Logistic Regression correctly identify only `3/12` and `1/12` suspicious test rows).
- **Offline demonstration only:** Intended strictly as an offline ML evaluation and classroom demonstration inside E-SAG—not real-time browser protection or live phishing blocking.

## How to Run & Test (Ubuntu `.venv`)

```bash
# Regenerate evaluation metrics and ml_results.json
.venv/bin/python esag/ml/train_eval.py

# Run ML unit tests
.venv/bin/python -m pytest tests/test_ml.py -v
```
