# Security

## Model

tco is a command line program that **reads a YAML scenario, computes costs, and writes files**. It starts no service, opens no
network connection and runs no code from its input.

- **What it reads:** the scenario YAML, parsed with `yaml.safe_load` (no object construction, no code) and then validated: every
  key and every number is checked, and anything unexpected is an error (exit code 2). A `report.json` or `bench.json` given to
  `render` is parsed as JSON and only its fields are read.
- **What it writes:** only where the options say: `example -o`, `run --out`, `bench --out`, `render -o` and `--figure`.
- **The Docker image** runs as an unprivileged user and works with a read-only root filesystem (plus `--tmpfs /tmp` for
  matplotlib's cache), no capabilities and no network (`--network none`); see `tools/docker_e2e.sh`.
- **No real data** is in the repository: the example is made of illustrative numbers.

## Reporting

If you find a vulnerability, please open a private security advisory on the GitHub repository (Security tab) rather than a
public issue.
