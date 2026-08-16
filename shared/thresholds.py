"""Decision thresholds shared between training-time validation and the consumer.

The ML score only becomes a fraud flag once it crosses a threshold. That number
has to be the same in both places: if the model is validated at one threshold and
served at another, the precision/recall bar in `ml/validate.py` is describing
behaviour the pipeline never runs.

This module is the single definition, imported by both, so the two cannot drift.
"""

# Score at or above which the ML layer flags a transaction. Set above 0.5 because
# the rule engine already catches the blunt cases; the model earns its place by
# adding confident catches, not by second-guessing borderline ones.
ML_FRAUD_THRESHOLD = 0.7
