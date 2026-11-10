# Analysis

Source: [`report.json`](report.json) (the bundled example scenario, 20,000 Monte Carlo variants, seed 1) and
[`bench.json`](bench.json) (one run in Docker on Linux x86_64 with 12 CPUs, Python 3.14.10, NumPy 2.5.4; medians of 5 runs). Every
price in the example is an assumption; read the structure of the results, not the euros.

## 1. What the home server costs

| Item | EUR over 60 months |
|---|---|
| Hardware purchases (including replacements) | €2,230 |
| Electricity | €1,429 |
| Expected failures (spares) | €178 |
| Recurring | €420 |
| **Cash spent** | **€4,258** |
| Residual value of the hardware | -€236 |
| **Net cost** | **€4,021** |

- **Hardware is 52.4% of the cash**, electricity 33.6%. The parts draw 103 W on average over a day (overhead x1.1
  included), so electricity is a third of the cash and the purchase is half of it.
- **Nothing is replaced inside the horizon**: no part has a life shorter than 60 months, so the €2,230 is the original purchase and the residual value is
  what remains of the straight-line life (€236).

## 2. Against each cloud alternative

| Cloud alternative | Bill over 60 months | A month | Home server saves (net) | Saves (cash only) | Break-even |
|---|---|---|---|---|---|
| Cheap object storage + small VPS | €9,810 | €164 | €5,789 | €5,552 | month 21 (2027-09) |
| Flat-rate storage box + small VPS | €2,700 | €45 | -€1,321 | -€1,558 | not within 60 months |
| Large-provider storage + managed database | €38,835 | €647 | €34,814 | €34,577 | month 5 (2026-05) |

- **The answer depends on which cloud you compare with.** The home server is €67 a month net: cheaper than two of the three
  alternatives, dearer than the flat-rate box (€45 a month, a price that does not grow with the data).
- **Break-even comes late when the cloud is cheap**: 21 months against the cheap object storage, because €2,230 is
  spent in month 0 and the cloud bill is paid a little each month.

## 3. What moves the answer

Each group of numbers 20.0% lower and 20.0% higher, the rest as written: the width of the resulting range of the saving.

| Group | Cheap object storage + small VPS | Flat-rate storage box + small VPS | Large-provider storage + managed database |
|---|---|---|---|
| Cloud prices | €3,924 | €1,080 | €15,534 |
| Storage needed | €3,444 | €0 | €12,054 |
| Hardware prices | €869 | €869 | €869 |
| Hardware life | €821 | €821 | €821 |
| Electricity price | €572 | €572 | €572 |
| Power draw of the hardware | €572 | €572 | €572 |
| Recurring costs | €168 | €168 | €168 |
| Time spent at load | €146 | €146 | €146 |
| Failure rate | €71 | €71 | €71 |

- **The cloud side dominates.** Against the cheap object storage the cloud price and the storage needed swing the saving by €3,924 and
  €3,444; the largest group on the home-server side, hardware prices, swings it by €869, 22% of the cloud-price swing.
- **Electricity price and power draw have the same effect by construction**: both multiply the energy bill, so their rows are equal.
- **The flat-rate box has no storage item**, so the storage-needed row is zero for it: its bill does not depend on how much you store (up to its limit).

## 4. Monte Carlo

Every group drawn independently from a triangular distribution peaking at the value as written, with the spread in `uncertainty`.

| Cloud alternative | Home server cheaper | 5th percentile | Median | 95th percentile |
|---|---|---|---|---|
| Cheap object storage + small VPS | 100.0% | €3,411 | €5,715 | €8,352 |
| Flat-rate storage box + small VPS | 0.0% | -€2,062 | -€1,335 | -€649 |
| Large-provider storage + managed database | 100.0% | €26,191 | €34,535 | €44,232 |

- **Two of the three conclusions are not close**: the home server wins in all 20,000 variants against the cheap object storage and against the large
  provider, and in 3 of 20,000 against the flat-rate box. The uncertainty in the inputs does not change which side is cheaper.
- **The width of the range still matters**: against the cheap object storage the saving runs from €3,411 to €8,352 between the 5th and the 95th percentile.

## 5. The value of your time

The example has 3 hours of administration a month at no value. The saving against the cheap object storage is €5,789 over
60 months, so the home server stays cheaper as long as an hour of your time is worth less than €5,789 / (3 x 60) = €32.
Against the flat-rate box it is already dearer at no value.

## 6. Speed

| Variants | Time | Variants per second | Literal simulation (extrapolated) |
|---|---|---|---|
| 1,000 | 6.8 ms | 146,035 | 10.5 s |
| 10,000 | 64.3 ms | 155,404 | 104.7 s |
| 100,000 | 651.6 ms | 153,462 | 1,046.7 s |
| 1,000,000 | 5,862.9 ms | 170,565 | 10,467.1 s |

- **Vectorising pays 1,785 times at a million variants**: one variant by the literal simulation takes 10.5 ms, one variant in a large batch 5.9 µs.
- **A batch is cheaper per variant than a single evaluation**: one evaluation alone takes 313 µs, 53 times the per-variant time in a batch of a million.
- **Time grows a little faster than the horizon**: 480 months take 10.1 times as long as 60 for 8 times the months.
- **Agreement**: 51 comparisons of every monthly cost, the residual value and every break-even month; the largest relative difference is 1.46e-14.

## What these numbers do not say

- They describe a scenario made of assumed prices; with your numbers the conclusions can reverse (see the flat-rate box).
- Straight-line life, cash purchases and fixed capacity; see [`limitations.md`](limitations.md).
- The speed figures are medians of 5 runs on one computer; the literal-simulation column is an extrapolation, not a measurement.
