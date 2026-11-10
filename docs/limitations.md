# Limitations

- **Every price in the example is an assumption.** Hardware prices, watts, electricity and cloud prices are round figures of
  the right order of magnitude, not quotes; the answer is only as good as the numbers you put in. Check the providers' price pages.
- **The home server's capacity is fixed.** The hardware you list is what you have; if the data outgrows it, add the extra disks to
  the scenario. Cloud storage, by contrast, grows with `tb_growth_per_year` and is paid for as it grows.
- **Straight-line life and cash purchases.** Parts are replaced on a fixed schedule; real parts die earlier or later, and used
  hardware sells for more than a straight line says. The expected-failure line covers spares, not the schedule.
- **Prices change in yearly steps, not by the month**, and the same rate applies to everything in the group.
- **Your time is free unless you value it.** `hourly_value_eur` is 0 by default; with a realistic value the home server loses
  against the cheap cloud scenarios.
- **No tax, no VAT, no currency conversion, no financing cost.** Money spent today and money spent in five years are added without
  discounting.
- **Availability and quality are not priced.** A cloud service has an SLA, redundancy and no power cuts at home; the model has no
  term for the cost of an outage or of the time to restore a backup.
- **Monte Carlo draws groups independently.** In reality prices move together (electricity and cloud both follow inflation), and a
  triangular distribution is a convenient shape, not a measurement.
- **Times are medians of a few runs on one computer.**
