import json
from pathlib import Path

from esag.ml.train_eval import (
    DATA_DIR,
    LABEL_MEANINGS,
    OUTPUT_JSON,
    load_dataset,
    preprocess_dataset,
    run_experiment,
)

EXPECTED_MODELS = {
    "Naive Bayes",
    "Decision Tree",
    "Random Forest",
    "Logistic Regression",
}


def test_load_and_preprocess_dataset() -> None:
    """Verify the UCI ARFF dataset loads and deduplicates cleanly."""
    df = load_dataset(DATA_DIR)
    assert df.shape == (1353, 10)

    X, y, stats = preprocess_dataset(df)
    assert stats["dataset_rows_raw"] == 1353
    assert stats["duplicates_removed"] == 629
    assert stats["dataset_rows_clean"] == 724
    assert len(X) == 724
    assert len(y) == 724
    assert list(X.columns) == [
        "SFH",
        "popUpWidnow",
        "SSLfinal_State",
        "Request_URL",
        "URL_of_Anchor",
        "web_traffic",
        "URL_Length",
        "age_of_domain",
        "having_IP_Address",
    ]


def test_run_experiment_generates_metrics_and_confusion_matrices(
    tmp_path: Path,
) -> None:
    """Verify held-out evaluation outputs metrics, confusion matrices, samples, and notes."""
    out_file = tmp_path / "ml_results.json"
    results = run_experiment(output_path=out_file)

    assert out_file.exists()
    persisted = json.loads(out_file.read_text(encoding="utf-8"))
    assert persisted == results

    assert results["train_rows"] == 579
    assert results["test_rows"] == 145
    assert results["label_meanings"] == LABEL_MEANINGS
    assert results["best_model"] in EXPECTED_MODELS
    assert set(results["models"].keys()) == EXPECTED_MODELS

    for metrics in results["models"].values():
        for key in ("accuracy", "precision", "recall", "f1_score"):
            assert 0.0 <= metrics[key] <= 1.0

        cm = metrics["confusion_matrix"]
        assert len(cm) == 3
        assert all(len(row) == 3 for row in cm)
        assert sum(sum(row) for row in cm) == results["test_rows"]

    samples = results["sample_examples"]
    assert len(samples) == 5
    actual_labels = {sample["actual_label"] for sample in samples}
    assert actual_labels == {"-1", "0", "1"}

    for sample in samples:
        assert set(sample["features"].keys()) == set(results["features"])
        assert sample["actual_label"] in LABEL_MEANINGS
        assert sample["predicted_label"] in LABEL_MEANINGS
        assert set(sample["predictions_by_model"].keys()) == EXPECTED_MODELS

    assert len(results["limitations"]) >= 3


def test_checked_in_ml_results_json_is_valid() -> None:
    """Verify the exported ml_results.json artifact is readable for the PySide6 UI."""
    assert OUTPUT_JSON.exists()
    data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    assert data["label_meanings"] == LABEL_MEANINGS
    assert set(data["models"].keys()) == EXPECTED_MODELS
    assert len(data["sample_examples"]) == 5
    assert data["limitations"]
