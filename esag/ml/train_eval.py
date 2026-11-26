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


def run_experiment() -> dict:
    # 1. Load dataset & Exploratory Data Analysis (EDA)
    df = load_dataset(DATA_DIR)
    print("\n--- Exploratory Data Analysis ---")
    print("Original shape (rows, cols):", df.shape)
    print("Columns:", list(df.columns))
    print("Missing values total:", int(df.isna().sum().sum()))

    # 2. Preprocessing
    df = df.dropna()
    before_dedup = len(df)
    df = df.drop_duplicates()
    print(f"Removed {before_dedup - len(df)} duplicate rows. Clean shape: {df.shape}")

    # Assume the last column is the target label (standard for UCI datasets)
    target_col = df.columns[-1]
    X = df.drop(columns=[target_col])
    y = df[target_col]

    print("Target column:", target_col)
    print("Class distribution:\n", y.value_counts())

    # 3. Train / Test Split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 4. Initialize the 4 models from Figure 3.4
    models = {
        "Naive Bayes": GaussianNB(),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    }

    # 5. Train & Evaluate on Test Set
    results = {
        "dataset_rows_clean": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "features": list(X.columns),
        "classes": [str(c) for c in sorted(y.unique())],
        "models": {},
    }

    print("\n--- Model Evaluation (Test Set) ---")
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()

        results["models"][name] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": cm,
        }

        print(f"\n[{name}]")
        print(f"  Accuracy : {acc:.4f}")
        print(f"  Precision: {prec:.4f}")
        print(f"  Recall   : {rec:.4f}")
        print(f"  F1-score : {f1:.4f}")
        print(f"  Confusion Matrix: {cm}")

    # 6. Save results for the PySide6 GUI & final report
    OUTPUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved evaluation report to: {OUTPUT_JSON}")
    return results


if __name__ == "__main__":
    run_experiment()