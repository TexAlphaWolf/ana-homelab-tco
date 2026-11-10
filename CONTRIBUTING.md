# Contributing

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest --cov
```

No service is needed. `TCO_TEST_DRAWS` and `TCO_TEST_SEED` run the same tests with more (or different) random variants and scenarios
(CI also uses 200 variants with seed 11).

Rules that keep the project honest:

- **A new cost needs both implementations.** Add it to `model.py` (vectorised) and to `reference.py` (the literal loop), compare
  them in `verify.py`, and add a test with a hand-computed value in `tests/test_model.py`.
- **A new group of parameters** goes in `config.GROUPS` with a label and a default uncertainty, and in `model.Variants` users; the
  tornado and Monte Carlo pick it up.
- **Numbers in the README come from `docs/report.json` and `docs/bench.json`**, and `tests/test_docs.py` checks them. After a
  change to the example or a new measurement (`tools/run_full.ps1`), regenerate them (`tco run --out`, copy `bench.json`) and update
  the text if a number moved.
