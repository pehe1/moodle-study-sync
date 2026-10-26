$ErrorActionPreference='Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$runtimeFile = Join-Path $projectDirectory 'private\runtime.local.json'
if (Test-Path -LiteralPath $runtimeFile) {
    $env:MOODLE_STUDY_SYNC_HOME = (Get-Content -LiteralPath $runtimeFile -Raw -Encoding UTF8 | ConvertFrom-Json).private_home
}
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
Set-Location -LiteralPath $projectDirectory
& (Join-Path $projectDirectory '.venv\Scripts\python.exe') -m moodle_study_sync.run --max-uploads 300
exit $LASTEXITCODE
