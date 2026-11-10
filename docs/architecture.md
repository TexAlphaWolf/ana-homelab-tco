# Architecture

```text
scenario.yaml --> config.py (checked, frozen dataclasses)
                      |
        +-------------+--------------------------+
        v                                        v
   model.py (NumPy, many variants at once)   reference.py (plain loops, day by day, hour by hour)
        |                                        |
        +--> sensitivity.py (tornado, Monte Carlo)+--> verify.py  <-- compares the two
        |
        v
   analysis.py (one dictionary) --> report.json --> report.py (Markdown, figures)
```

| File | Role |
|---|---|
| `config.py` | Reads and validates the YAML: unknown keys, wrong types, out-of-range numbers and a load below idle are errors that name the field (`hardware[2].life_months`). |
| `model.py` | The cost model on arrays of shape (variants, months): hardware purchases, energy, failures, recurring, time, cloud bills, residual value, break-even. |
| `reference.py` | The same numbers, computed the slow and literal way, to check the model against. |
| `sensitivity.py` | One-at-a-time sensitivity and the Monte Carlo run (chunked, so a million variants fit in memory). |
| `verify.py` | The comparison of model and reference. |
| `analysis.py` | Collects everything the report says into one JSON-able dictionary. |
| `report.py` | Markdown and figures from `report.json` / `bench.json`; both are pure functions of the JSON. |
| `bench.py` | Timings and the agreement check. |
| `cli.py` | `example`, `validate`, `run`, `verify`, `bench`, `render`. |

Exit codes: 0 success, 1 a verification mismatch, 2 an error (invalid scenario file, bad options).

## Design choices

- **One model, any number of variants.** A single evaluation is a variant set of size one, so the sensitivity study and the Monte
  Carlo run use exactly the code that produces the headline numbers.
- **Cash first.** Hardware is money out when it is bought; the residual value is a separate line, so that "when do I get my money
  back" and "what did it really cost" are both answered and neither is hidden in the other.
- **Real calendar.** Energy is charged on the real number of days of each month, so a leap February costs a day more.
- **The reports are functions of JSON.** `tco render report.json` rebuilds the Markdown and the figure exactly; the tests check
  that the committed `docs/*.md` are what the JSON renders to.
