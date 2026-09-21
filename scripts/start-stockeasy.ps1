$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root '.venv\Scripts\python.exe'
$vite = Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
$appUrl = 'http://127.0.0.1:5173'
$healthUrl = 'http://127.0.0.1:8000/api/health'
$backendProcess = $null
$frontendProcess = $null

function Test-StockEasyUrl([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Wait-StockEasyUrl([string]$Url, [System.Diagnostics.Process]$Process) {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($Process.HasExited) {
            throw "Un proceso de StockEasy terminó antes de iniciar correctamente."
        }
        if (Test-StockEasyUrl $Url) { return }
        Start-Sleep -Milliseconds 250
        $Process.Refresh()
    }
    throw "StockEasy no respondió a tiempo en $Url"
}

try {
    if ((Test-StockEasyUrl $healthUrl) -and (Test-StockEasyUrl $appUrl)) {
        Start-Process $appUrl
        return
    }
    if ((Test-StockEasyUrl $healthUrl) -or (Test-StockEasyUrl $appUrl)) {
        throw 'Los puertos 8000 o 5173 ya están ocupados por otro proceso.'
    }
    if (-not (Test-Path -LiteralPath $python)) {
        throw 'No se encontró el entorno Python. Ejecuta .\scripts\dev.ps1 install primero.'
    }
    if (-not (Test-Path -LiteralPath $vite)) {
        throw 'No se encontró Vite. Ejecuta .\scripts\dev.ps1 install primero.'
    }

    $backendProcess = Start-Process -FilePath $python -ArgumentList @('-m', 'app.desktop') -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -PassThru
    Wait-StockEasyUrl $healthUrl $backendProcess

    $node = (Get-Command node.exe -ErrorAction Stop).Source
    $frontendProcess = Start-Process -FilePath $node -ArgumentList @("`"$vite`"", '--host', '127.0.0.1') -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru
    Wait-StockEasyUrl $appUrl $frontendProcess

    Start-Process $appUrl
    Wait-Process -Id $backendProcess.Id
} catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($_.Exception.Message, 'StockEasy', 'OK', 'Error') | Out-Null
} finally {
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force
    }
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
}
