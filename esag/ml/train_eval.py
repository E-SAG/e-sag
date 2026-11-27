import json
from pathlib import Path

import pandas as pd
from scipy.io import arff
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_JSON = Path(__file__).parent / "ml_results.json"

# UCI Website Phishing (ID 379) encodes Legitimate=1, Suspicious=0, Phishy=-1.
LABEL_MEANINGS: dict[str, str] = {
    "-1": "Phishing",
    "0": "Suspicious",
    "1": "Legitimate",
}

LIMITATIONS: list[str] = [
    (
        "Static historical features: trained on the UCI Website Phishing dataset "
        "(ID 379, 2014/2016 release) using 9 pre-extracted discrete indicators rather "
        "than live URL or HTML scraping."
    ),
    (
        "Duplicate removal impact: 629 of 1,353 raw rows (~46.5%) were exact "
        "duplicates and removed, leaving 724 unique rows (579 train / 145 test)."
    ),
    (
        "Class 0 ('Suspicious') imbalance: only 61 unique rows (~8.4% of clean "
        "data, 12 rows in the 20% test split), reducing recall and precision on "
        "borderline cases."
    ),
    (
        "Offline demonstration only: intended for the PySide6 UI 'View ML "
        "demonstration' tab, not real-time browser protection or live phishing "
        "blocking."
    ),
]


def load_dataset(data_dir: Path) -> pd.DataFrame:
    """Find and load the UCI dataset (.csv or .arff) from esag/ml/data/."""
    csv_files = list(data_dir.glob("*.csv"))
    arff_files = list(data_dir.glob("*.arff"))

    if csv_files:
        print(f"Loading CSV: {csv_files[0].name}")
        return pd.read_csv(csv_files[0])

    if arff_files:
        print(f"Loading ARFF: {arff_files[0].name}")
        raw_data, _ = arff.loadarff(arff_files[0])
        df = pd.DataFrame(raw_data)
        # ARFF categorical values load as bytes (e.g., b'-1'); decode to text/numbers
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda v: v.decode("utf-8") if isinstance(v, bytes) else v
                )
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass
        return df

    raise FileNotFoundError(
        f"No .csv or .arff dataset found in {data_dir}. "
        "Download the UCI Website Phishing dataset and place it there."
    )


def preprocess_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict[str, int]]:
    """Drop missing values and exact duplicates, then split into features and target."""
    raw_rows = len(df)
    df_clean = df.dropna().drop_duplicates()
    clean_rows = len(df_clean)
    stats = {
        "dataset_rows_raw": raw_rows,
        "duplicates_removed": raw_rows - clean_rows,
        "dataset_rows_clean": clean_rows,
    }

    target_col = df_clean.columns[-1]
    X = df_clean.drop(columns=[target_col])
    y = df_clean[target_col]
    return X, y, stats


def build_models() -> dict[str, object]:
    """Create the four baseline classifiers for offline phishing demonstration."""
    return {
        "Naive Bayes": GaussianNB(),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    }


def evaluate_models(
    models: dict[str, object],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    class_labels: list[int],
) -> tuple[dict[str, dict], dict[str, list[int]]]:
    """Fit each classifier on train data and compute held-out test metrics."""
    metrics_by_model: dict[str, dict] = {}
    predictions_by_model: dict[str, list[int]] = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        predictions_by_model[name] = [int(v) for v in y_pred]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        cm = confusion_matrix(y_test, y_pred, labels=class_labels).tolist()

        metrics_by_model[name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": cm,
        }

    return metrics_by_model, predictions_by_model


def select_sample_examples(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    predictions_by_model: dict[str, list[int]],
    best_model_name: str,
    count: int = 5,
) -> list[dict]:
    """Select representative held-out test rows covering all classes for the UI demo."""
    selected_positions: list[int] = []
    seen_classes: set[int] = set()
    y_values = [int(v) for v in y_test]

    # Pick one example from each class first so the UI demo shows all three labels.
    for pos, label in enumerate(y_values):
        if label not in seen_classes:
            selected_positions.append(pos)
            seen_classes.add(label)
        if len(selected_positions) == count:
            break

    for pos in range(len(y_values)):
        if len(selected_positions) >= count:
            break
        if pos not in selected_positions:
            selected_positions.append(pos)

    samples: list[dict] = []
    for sample_idx, pos in enumerate(selected_positions, start=1):
        row = X_test.iloc[pos]
        actual_code = str(y_values[pos])
        best_pred_code = str(predictions_by_model[best_model_name][pos])

        model_preds = {
            name: {
                "label": str(preds[pos]),
                "label_name": LABEL_MEANINGS.get(str(preds[pos]), str(preds[pos])),
            }
            for name, preds in predictions_by_model.items()
        }

        samples.append(
            {
                "sample_id": sample_idx,
                "row_index": int(X_test.index[pos]),
                "features": {col: int(val) for col, val in row.items()},
                "actual_label": actual_code,
                "actual_label_name": LABEL_MEANINGS.get(actual_code, actual_code),
                "predicted_label": best_pred_code,
                "predicted_label_name": LABEL_MEANINGS.get(
                    best_pred_code, best_pred_code
                ),
                "predictions_by_model": model_preds,
            }
        )

    return samples


def run_experiment(
    output_path: Path | None = OUTPUT_JSON,
    data_dir: Path = DATA_DIR,
) -> dict:
    """Run offline phishing train/eval and optionally export results JSON for the UI."""
    df = load_dataset(data_dir)
    print("\n--- Exploratory Data Analysis ---")
    print("Original shape (rows, cols):", df.shape)
    print("Columns:", list(df.columns))
    print("Missing values total:", int(df.isna().sum().sum()))

    X, y, stats = preprocess_dataset(df)
    print(
        f"Removed {stats['duplicates_removed']} duplicate rows. "
        f"Clean shape: ({stats['dataset_rows_clean']}, {len(df.columns)})"
    )
    print("Target column:", df.columns[-1])
    print("Class distribution:\n", y.value_counts())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    class_labels = [int(c) for c in sorted(y.unique())]
    models = build_models()
    metrics_by_model, predictions_by_model = evaluate_models(
        models, X_train, X_test, y_train, y_test, class_labels
    )

    best_model_name = max(
        metrics_by_model,
        key=lambda name: (
            metrics_by_model[name]["accuracy"],
            metrics_by_model[name]["f1_score"],
        ),
    )

    sample_examples = select_sample_examples(
        X_test, y_test, predictions_by_model, best_model_name, count=5
    )

    class_counts = {str(k): int(v) for k, v in y.value_counts().sort_index().items()}
    results = {
        "dataset_rows_raw": stats["dataset_rows_raw"],
        "duplicates_removed": stats["duplicates_removed"],
        "dataset_rows_clean": stats["dataset_rows_clean"],
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "features": list(X.columns),
        "classes": [str(c) for c in class_labels],
        "label_meanings": {
            c: LABEL_MEANINGS[c] for c in [str(c) for c in class_labels] if c in LABEL_MEANINGS
        },
        "class_distribution_clean": class_counts,
        "best_model": best_model_name,
        "models": metrics_by_model,
        "sample_examples": sample_examples,
        "limitations": LIMITATIONS,
    }

    print("\n--- Model Evaluation (Test Set) ---")
    for name, metric in metrics_by_model.items():
        print(f"\n[{name}]")
        print(f"  Accuracy : {metric['accuracy']:.4f}")
        print(f"  Precision: {metric['precision']:.4f}")
        print(f"  Recall   : {metric['recall']:.4f}")
        print(f"  F1-score : {metric['f1_score']:.4f}")
        print(f"  Confusion Matrix: {metric['confusion_matrix']}")

    if output_path is not None:
        output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"\nSaved evaluation report to: {output_path}")

    return results


if __name__ == "__main__":
    run_experiment()
