import sys
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from ml.validate import validate, assert_meets_bar

FEATURE_COLUMNS = [f"V{i}" for i in range(1, 29)]


def train(csv_path: str, model_out: str) -> dict:
    df = pd.read_csv(csv_path)
    X, y = df[FEATURE_COLUMNS], df["Class"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = XGBClassifier(eval_metric="logloss", random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, model_out)

    return {"X_test": X_test, "y_test": y_test, "model": model}


if __name__ == "__main__":
    result = train(sys.argv[1], sys.argv[2])
    metrics = validate(result["model"], result["X_test"], result["y_test"])
    print(f"precision={metrics['precision']:.3f} recall={metrics['recall']:.3f}")
    assert_meets_bar(metrics)
