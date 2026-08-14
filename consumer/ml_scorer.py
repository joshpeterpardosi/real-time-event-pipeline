import joblib
from shared.schema import TransactionEvent


class MLScorer:
    def __init__(self, model_path: str):
        try:
            self._model = joblib.load(model_path)
        except Exception as exc:
            raise RuntimeError(f"failed to load ML model from {model_path}") from exc

    def score(self, event: TransactionEvent) -> float | None:
        if event.features is None:
            return None
        return float(self._model.predict_proba([event.features])[0][1])
