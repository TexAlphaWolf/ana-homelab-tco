# Method

## What is computed

For a horizon of `horizon_months` calendar months starting at `start`, the model produces a **monthly cash cost** for the home
server and for each cloud alternative, and compares the sums.

**Home server, per month**

| Item | How it is computed |
|---|---|
| Hardware purchases | Each part (price x count) is bought in month 0 and again every `life_months`. A purchase in the last months still counts in full: this is the cash view. |
| Electricity | For every hour of the day: watts = (idle + (load - idle) x u) x overhead, with `u` the share of that hour spent at load; cost = watts / 1000 x price of that hour; summed over 24 hours, times the real number of days of that calendar month, times (1 + yearly increase) to the power of the elapsed whole years. |
| Expected failures | price x count x annual failure rate / 12, every month: the expected cost of spares, not a lump sum when a disk dies. |
| Recurring | A flat monthly amount for each listed item (domain, off-site backup, ...). |
| Your time | `hours_per_month` x `hourly_value_eur`; zero unless you give your time a value. |

**Residual value.** At the end of the horizon, each part's last purchase has some straight-line life left; its value (price x
share of life left) is shown separately and subtracted to give the **net cost**. The headline comparison uses the net cost; the
**break-even** uses cash.

**Cloud alternative, per month.** Each item is one of: `fixed` (a flat monthly price), `storage` (TB x price per TB-month, with the
TB growing linearly by `tb_growth_per_year`) or `egress` (TB per month x price per TB). The sum is multiplied by (1 + cloud yearly
increase) to the power of the elapsed whole years.

**Comparison.** *Home server saves* = cloud bill over the horizon - home server net cost. *Break-even* = the first month number
in which the cumulative cash spent on the home server is no more than the cumulative cloud bill (0 = never within the horizon).

## Variants, sensitivity and Monte Carlo

The parameters are in nine groups (electricity price, power draw, time at load, hardware prices, hardware life, failure rate,
recurring costs, cloud prices, storage needed). A *variant* multiplies each group by a factor; 1 is the scenario as written. The
model evaluates many variants at once (one row per variant, one column per month).

- **Sensitivity (tornado):** each group in turn at 1 - s and 1 + s (default s = 20%), the rest as written; the result is what the
  home server saves in each case.
- **Monte Carlo:** every group gets an independent factor from a triangular distribution that peaks at 1 and reaches 1 +/- the
  spread in `uncertainty` (defaults 15% to 50% depending on the group). The report gives the share of variants in which the home
  server is cheaper, percentiles of the saving, and the share with a break-even inside the horizon.

## How it is checked

`reference.py` computes the same costs without arrays or closed forms: it loops over the months of the calendar, over each day of
each month and over each of the 24 hours for the energy; buys hardware by walking forward in time; and builds each cloud bill
month by month. `verify` compares the two on the scenario as written and on random variants within its uncertainty: every
monthly component, the residual value, every cloud bill and every break-even month, with a relative tolerance of 1e-9. The tests
repeat this on randomly generated scenarios (random hardware, tariffs, profiles, growth and cloud items), and show that the check
can fail (a model that is 0.1% off, or a wrong break-even, is reported).

## The benchmark

`bench` times, for each number of variants, a full Monte Carlo run (median of `--repeat` runs); the time of one variant of the
literal simulation (so that the cost of checking everything that way can be extrapolated); the throughput for horizons from 60 to
480 months; and runs `verify` on `--draws` random variants.
