# The full measurement on your own computer, in Docker (no network, read-only root, no capabilities), from Windows
# PowerShell: how fast the cost model is, for growing numbers of Monte Carlo variants, and that it agrees with the literal
# simulation.
# Usage: .\tools\run_full.ps1 [-Sizes 1000,10000,100000,1000000] [-Repeat 5] [-Draws 50] [-Out results]
param(
    [string]$Sizes = "1000,10000,100000,1000000",
    [int]$Repeat = 5,
    [int]$Draws = 50,
    [string]$Out = "results"
)
# Windows PowerShell 5.1 turns anything a program writes on stderr into an error under "Stop": docker and tco print
# their progress there, so only the exit code is looked at.
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$outFull = (Resolve-Path -LiteralPath $Out).Path

docker build -t tco .
if ($LASTEXITCODE -ne 0) { Write-Host "docker build failed"; exit 1 }

Write-Host "== bench (sizes $Sizes, $Repeat runs each, $Draws random variants checked) =="
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --network none -v "${outFull}:/out" tco bench --sizes $Sizes --repeat $Repeat --draws $Draws --out /out
if ($LASTEXITCODE -ne 0) { Write-Host "bench failed (exit code $LASTEXITCODE)"; exit 1 }
Write-Host "Done. Send me $Out\bench.json, $Out\bench.md and $Out\summary.png."
