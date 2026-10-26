param([string]$PrivateHome)
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$runtimeFile = Join-Path $projectDirectory 'private\runtime.local.json'
if (-not $PrivateHome) {
    if (Test-Path -LiteralPath $runtimeFile) {
        $PrivateHome = (Get-Content -LiteralPath $runtimeFile -Raw -Encoding UTF8 | ConvertFrom-Json).private_home
    } else {
        $PrivateHome = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'MoodleStudySync'
    }
}
$googleDirectory = Join-Path $PrivateHome 'google'
New-Item -ItemType Directory -Path $googleDirectory -Force | Out-Null
$privateAcl = New-Object System.Security.AccessControl.DirectorySecurity
$privateAcl.SetAccessRuleProtection($true, $false)
$userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$privateAcl.SetOwner($userSid)
$privateRule = New-Object System.Security.AccessControl.FileSystemAccessRule($userSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$privateAcl.AddAccessRule($privateRule)
Set-Acl -LiteralPath $googleDirectory -AclObject $privateAcl
$env:NOTEBOOKLM_HOME=$googleDirectory
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$client = Join-Path $projectDirectory '.venv\Scripts\notebooklm.exe'
for ($attempt=0; $attempt -lt 2; $attempt++) {
    & $client --profile study-sync login --browser msedge --browser-timeout 900
    if ($LASTEXITCODE -ne 0) { break }
    $checkText = & $client --profile study-sync auth check --test --json
    $checkExit = $LASTEXITCODE
    if ($checkExit -eq 0) {
        $check = ($checkText -join [Environment]::NewLine) | ConvertFrom-Json
        if ($check.status -eq 'ok' -and $check.checks.token_fetch -eq $true) {
            Write-Host 'Google conectado. A rotina pode atualizar os materiais.'
            exit 0
        }
    }
    Write-Host 'A verificacao ainda nao passou. Tentando concluir a mesma sessao novamente.'
}
Write-Host 'Nao foi possivel validar o acesso. A coleta local continua preservada.'
exit 2
