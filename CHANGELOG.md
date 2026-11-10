# Changelog

## 1.0.0

First release.

- A monthly cash model of a home server (hardware purchases and replacements, electricity by hour of day on the real calendar,
  expected failures, recurring costs, valued time, residual value) against any number of cloud alternatives (flat, per-TB with
  growth, egress).
- Sensitivity (tornado) over nine groups of parameters, and a Monte Carlo run with triangular uncertainty.
- A literal day-by-day, hour-by-hour simulation and a verifier that compares it with the vectorised model.
- A scenario file (YAML) with strict validation and a bundled example.
- A report (JSON, Markdown, figure) rebuilt exactly from its JSON, and a benchmark of the model.
- A command line (`example`, `validate`, `run`, `verify`, `bench`, `render`) with exit codes for a pipeline.
- Docker image (no network, read-only, no capabilities); CI on Python 3.11 to 3.14, Linux, Windows and macOS.
