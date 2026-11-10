# Benchmark

Run on Linux x86_64, 12 CPUs, Python 3.14.10, NumPy 2.5.4; scenario `bundled example` (60 months, 3 cloud alternatives); seed 1; each time is the median of 5 runs; command `bench --sizes 1000,10000,100000,1000000 --repeat 5 --draws 50 --out /out`.

## 1. Monte Carlo by number of variants

Every variant is the whole scenario evaluated again (hardware purchases, 24 hours of energy for each month, every cloud bill and the break-even months). *Literal simulation* is the time of the day-by-day reference for one variant multiplied by the number of variants: an extrapolation, not a measurement.

| Variants | Time | Variants per second | Literal simulation (extrapolated) | Speed-up |
|---|---|---|---|---|
| 1,000 | 6.8 ms | 146,035 | 10.47 s | 1,529x |
| 10,000 | 64.3 ms | 155,404 | 104.67 s | 1,627x |
| 100,000 | 651.6 ms | 153,462 | 1,046.71 s | 1,606x |
| 1,000,000 | 5.86 s | 170,565 | 10,467.11 s | 1,785x |

One variant by the literal simulation takes 10.5 ms (median); by the vectorised model on its own, one evaluation takes 313 µs.

## 2. Time by horizon (10,000 variants)

| Horizon (months) | Time | Variants per second |
|---|---|---|
| 60 | 58.2 ms | 171,674 |
| 120 | 130.2 ms | 76,812 |
| 240 | 234.5 ms | 42,651 |
| 480 | 586.7 ms | 17,043 |

## 3. Agreement with the literal simulation

51 comparisons (the scenario as written and 50 random variants): every monthly cost, the residual value and every break-even month. Largest relative difference 1.46e-14 (tolerance 1e-09); all match.
