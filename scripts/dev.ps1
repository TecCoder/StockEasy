param([ValidateSet('install','backend','frontend','test','lint','format','migrate','seed')][string]$Task = 'backend')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$python = Join-Path $root '.venv/Scripts/python.exe'
function Invoke-Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}
switch ($Task) {
    'install' {
        Invoke-Checked { python -m venv .venv }
        Invoke-Checked { & $python -m pip install -e './backend[dev]' }
        Set-Location frontend
        Invoke-Checked { npm.cmd ci }
    }
    'backend' { Set-Location backend; Invoke-Checked { & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log } }
    'frontend' { Set-Location frontend; Invoke-Checked { npm.cmd run dev } }
    'migrate' { New-Item -ItemType Directory -Force -Path data | Out-Null; Set-Location backend; Invoke-Checked { & $python -m alembic upgrade head } }
    'seed' { Set-Location backend; Invoke-Checked { & $python -m app.cli create-user --username (Read-Host 'Username') } }
    'test' { Set-Location backend; Invoke-Checked { & $python -m pytest }; Set-Location ../frontend; Invoke-Checked { npm.cmd test } }
    'lint' { Set-Location backend; Invoke-Checked { & $python -m ruff check . }; Invoke-Checked { & $python -m mypy app }; Set-Location ../frontend; Invoke-Checked { npm.cmd run lint }; Invoke-Checked { npm.cmd run typecheck } }
    'format' { Set-Location backend; Invoke-Checked { & $python -m ruff format . }; Set-Location ../frontend; Invoke-Checked { npm.cmd run format } }
}
