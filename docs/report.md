# Total cost of ownership: Home server, four-bay build

60 months from 2026-01. Hardware bought up front is €2,230; the parts draw 103 W on average over a day (power-supply overhead x1.1 included). Electricity rises 2.0% a year, cloud prices 0.0% a year. Cash view: hardware is paid when bought and again when its life ends; what is left of its straight-line life at the end is shown as a residual value.

## 1. The home server

| Part | Count | Price each | Life (months) | Idle W | Load W | Failures a year |
|---|---|---|---|---|---|---|
| Server (CPU, board, RAM, PSU, case) | 1 | €900 | 72 | 35 | 120 | 2.0% |
| HDD 12 TB | 4 | €250 | 60 | 5 | 8 | 1.5% |
| NVMe SSD 2 TB | 1 | €120 | 60 | 1 | 5 | 1.0% |
| Rack switch 16 ports | 1 | €150 | 96 | 12 | 15 | 1.0% |
| Rack PDU and rack | 1 | €60 | 120 | 2 | 2 | 0.0% |

## 2. What it costs over 60 months

| Item | EUR |
|---|---|
| Hardware purchases (including replacements) | €2,230 |
| Electricity | €1,429 |
| Expected failures (spares) | €178 |
| Recurring (domain, off-site backup, ...) | €420 |
| Your time, valued | €0 |
| **Cash spent** | **€4,258** |
| Residual value of the hardware at the end | -€236 |
| **Net cost** | **€4,021** (€67 a month) |

## 3. Against the cloud

*Home server saves* is the cloud bill minus the home server's net cost; the break-even is the first month in which the cash spent on the home server (all of it, bought up front) is no more than the cloud bill so far.

| Cloud alternative | Cloud bill | A month | Home server saves | Break-even |
|---|---|---|---|---|
| Cheap object storage + small VPS | €9,810 | €164 | €5,789 | month 21 (2027-09) |
| Flat-rate storage box + small VPS | €2,700 | €45 | -€1,321 | not within 60 months |
| Large-provider storage + managed database | €38,835 | €647 | €34,814 | month 5 (2026-05) |

## 4. What moves the answer

Each group of numbers in turn 20.0% lower and 20.0% higher, the rest as written; the cell is what the home server saves over that cloud alternative (negative: it costs more). Largest effect first.

**Cheap object storage + small VPS**

| Group | At -20% | At +20% |
|---|---|---|
| Cloud prices | €3,827 | €7,751 |
| Storage needed | €4,067 | €7,511 |
| Hardware prices | €6,223 | €5,354 |
| Hardware life | €5,297 | €6,118 |
| Electricity price | €6,075 | €5,503 |
| Power draw of the hardware | €6,075 | €5,503 |
| Recurring costs | €5,873 | €5,705 |
| Time spent at load | €5,862 | €5,716 |
| Failure rate | €5,824 | €5,753 |

**Flat-rate storage box + small VPS**

| Group | At -20% | At +20% |
|---|---|---|
| Cloud prices | -€1,861 | -€781 |
| Hardware prices | -€887 | -€1,756 |
| Hardware life | -€1,813 | -€992 |
| Electricity price | -€1,035 | -€1,607 |
| Power draw of the hardware | -€1,035 | -€1,607 |
| Recurring costs | -€1,237 | -€1,405 |
| Time spent at load | -€1,248 | -€1,394 |
| Failure rate | -€1,286 | -€1,357 |
| Storage needed | -€1,321 | -€1,321 |

**Large-provider storage + managed database**

| Group | At -20% | At +20% |
|---|---|---|
| Cloud prices | €27,047 | €42,581 |
| Storage needed | €28,787 | €40,841 |
| Hardware prices | €35,248 | €34,379 |
| Hardware life | €34,322 | €35,143 |
| Electricity price | €35,100 | €34,528 |
| Power draw of the hardware | €35,100 | €34,528 |
| Recurring costs | €34,898 | €34,730 |
| Time spent at load | €34,887 | €34,741 |
| Failure rate | €34,849 | €34,778 |

## 5. Monte Carlo

20,000 variants (seed 1), every group of numbers drawn independently from a triangular distribution that peaks at the value as written and reaches the spread set in `uncertainty`.

| Cloud alternative | Home server cheaper | 5th percentile | Median | 95th percentile | Break-even within horizon |
|---|---|---|---|---|---|
| Cheap object storage + small VPS | 100.0% | €3,411 | €5,715 | €8,352 | 100.0% |
| Flat-rate storage box + small VPS | 0.0% | -€2,062 | -€1,335 | -€649 | 0.0% |
| Large-provider storage + managed database | 100.0% | €26,191 | €34,535 | €44,232 | 100.0% |
