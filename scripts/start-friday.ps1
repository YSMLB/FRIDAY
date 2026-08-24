$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "apps\backend"
$Desktop = Join-Path $Root "apps\desktop"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:BROWSER = "none"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

function Wait-Http($Url, $Tries = 50) {
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1
            if ($r.StatusCode -ge 200) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (Test-Path $ollama) {
    Start-Process $ollama -ArgumentList "serve" -WindowStyle Hidden
}

& (Join-Path $PSScriptRoot "free-port.ps1") -Port 8765
& (Join-Path $PSScriptRoot "free-port.ps1") -Port 5173

Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $Backend -WindowStyle Hidden

$node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
if (-not $node) { throw "Node.js is not installed." }
$viteJs = Join-Path $Desktop "node_modules\vite\bin\vite.js"
if (-not (Test-Path $viteJs)) { throw "Vite is not installed. Run npm install in apps/desktop." }
Start-Process -FilePath $node -ArgumentList @($viteJs, "--host", "127.0.0.1", "--port", "5173") -WorkingDirectory $Desktop -WindowStyle Hidden

if (-not (Wait-Http "http://127.0.0.1:8765/health" 60)) {
    throw "FRIDAY backend failed to start on port 8765"
}
if (-not (Wait-Http "http://127.0.0.1:5173" 60)) {
    throw "FRIDAY UI failed to start on port 5173"
}

Set-Location $Desktop
$tsc = Join-Path $Desktop "node_modules\typescript\bin\tsc"
& $node $tsc -p tsconfig.electron.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$electronExe = Join-Path $Desktop "node_modules\electron\dist\electron.exe"
if (-not (Test-Path $electronExe)) {
    throw "Electron is not installed. Run npm install in apps/desktop."
}
Start-Process -FilePath $electronExe -ArgumentList "." -WorkingDirectory $Desktop
