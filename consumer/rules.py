from collections import defaultdict, deque
from shared.schema import TransactionEvent
from consumer import reasons

AMOUNT_THRESHOLD = 5000.0
VELOCITY_MAX_COUNT = 5
VELOCITY_WINDOW_SECONDS = 60


class RuleEngine:
    def __init__(self):
        self._recent_timestamps: dict[str, deque] = defaultdict(deque)
        self._last_country: dict[str, str] = {}

    def evaluate(self, event: TransactionEvent, now_epoch: float) -> list[str]:
        reasons_triggered = []
        if event.amount > AMOUNT_THRESHOLD:
            reasons_triggered.append(reasons.AMOUNT_THRESHOLD)

        window = self._recent_timestamps[event.user_id]
        window.append(now_epoch)
        while window and now_epoch - window[0] > VELOCITY_WINDOW_SECONDS:
            window.popleft()
        if len(window) > VELOCITY_MAX_COUNT:
            reasons_triggered.append(reasons.VELOCITY)

        last_country = self._last_country.get(event.user_id)
        if last_country is not None and last_country != event.country:
            reasons_triggered.append(reasons.GEO_MISMATCH)
        self._last_country[event.user_id] = event.country

        return reasons_triggered
