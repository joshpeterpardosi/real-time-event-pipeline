# Dev environment

- Always run Python (pytest, scripts, etc.) via the project's `.venv`,
  never a global/system Python interpreter:
  `.venv/Scripts/python.exe -m pytest` (Windows).
- The global interpreter does not have `confluent-kafka` /
  `clickhouse-connect` installed. Running pytest through it makes
  `unittest.mock.patch("generator.producer.Producer")` (and similar
  targets that import those packages) fail with a misleading
  `AttributeError: module 'generator' has no attribute 'producer'`
  instead of the real `ModuleNotFoundError` - the missing-dependency
  import error gets silently swallowed by `mock.patch`'s target
  resolution. It looks like a broken test; it's actually the wrong
  interpreter.
- See README.md's "Running tests" section for the exact setup/run
  commands.
