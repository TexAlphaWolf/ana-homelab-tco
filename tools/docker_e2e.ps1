# End to end inside the image, from Windows PowerShell: the example scenario is written to a volume, validated, analysed,
# checked against the literal simulation and benchmarked (read-only root, no capabilities, no network). Needs Docker Desktop.
# Usage: .\tools\docker_e2e.ps1 [-Image tco]
param([string]$Image = "tco")
$ErrorActionPreference = "Stop"

$id = Get-Random
$vol = "tco-e2e-$id"
$secure = @("--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--network", "none", "-v", "${vol}:/data")

# Windows PowerShell 5.1 turns a program's message on stderr into an error under "Stop": the commands that are expected to
# fail run with errors not terminating, and only their exit code is looked at.
function Invoke-TcoCode([int[]]$Allowed, [string[]]$TcoArgs) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = docker run --rm @secure $Image @TcoArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    if ($Allowed -notcontains $code) { throw "tco $TcoArgs exited with $code : $out" }
    ($out | Out-String)
}
function Invoke-Tco([string[]]$TcoArgs) { Invoke-TcoCode @(0) $TcoArgs }
function Read-Volume($path) {
    $out = docker run --rm --entrypoint cat -v "${vol}:/data" $Image $path 2>$null
    if ($LASTEXITCODE -ne 0) { throw "cannot read $path" }
    ($out | Out-String)
}
function Assert-Contains($text, $needle) { if ($text -notmatch [regex]::Escape($needle)) { throw "expected '$needle' in: $text" } }

try {
    docker volume create $vol | Out-Null
    docker run --rm --user 0 -v "${vol}:/data" --entrypoint chown $Image 10001 /data
    if ($LASTEXITCODE -ne 0) { throw "could not prepare the volume" }

    Assert-Contains (Invoke-Tco @("example", "-o", "/data/home.yaml")) "written: /data/home.yaml"
    Assert-Contains (Invoke-Tco @("validate", "/data/home.yaml")) "5 hardware items"

    $run = Invoke-Tco @("run", "/data/home.yaml", "--samples", "2000", "--out", "/data/out")
    Assert-Contains $run "home server: cash"
    Assert-Contains $run "break-even month 21 (2027-09)"
    $md = Read-Volume "/data/out/report.md"
    Invoke-Tco @("render", "/data/out/report.json", "-o", "/data/out/again.md") | Out-Null
    if ((Read-Volume "/data/out/again.md") -ne $md) { throw "the report rebuilt from the JSON is not identical" }

    Assert-Contains (Invoke-Tco @("verify", "/data/home.yaml", "--draws", "5")) "6 of 6 comparisons agree with the literal simulation"

    Invoke-Tco @("bench", "/data/home.yaml", "--sizes", "500,1000", "--repeat", "1", "--draws", "3", "--out", "/data/bench") | Out-Null
    Assert-Contains (Read-Volume "/data/bench/bench.json") '"ok": true'

    Invoke-TcoCode @(2) @("validate", "/data/nope.yaml") | Out-Null
    Write-Host "docker end-to-end: OK"
}
finally {
    $ErrorActionPreference = "Continue"
    docker volume rm -f $vol 2>&1 | Out-Null
}
