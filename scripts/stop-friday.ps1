param(
    [switch]$Quiet
)

$PidFile = Join-Path $env:APPDATA "FRIDAY\pids.json"

function Stop-Port([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -and $c.OwningProcess -ne 0) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

if (Test-Path $PidFile) {
    try {
        $pids = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($id in @($pids.backend, $pids.ui, $pids.electron)) {
            if ($id) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
        }
    } catch { }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

Stop-Port 8765
Stop-Port 5173

Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'friday|apps\\desktop' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (-not $Quiet) { Write-Host "FRIDAY stopped." }
