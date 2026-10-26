param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$PrivateHome
)
$ErrorActionPreference = 'Stop'
$projectDirectory = (Resolve-Path -LiteralPath $ProjectRoot).Path
$privateDirectory = (Resolve-Path -LiteralPath $PrivateHome).Path
$env:MOODLE_STUDY_SYNC_HOME = $privateDirectory
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath $projectDirectory
$pythonProgram = Join-Path $projectDirectory '.venv\Scripts\python.exe'
& $pythonProgram -m moodle_study_sync.run --max-uploads 300
$syncExitCode = $LASTEXITCODE
if ($syncExitCode -eq 4) { exit 4 }

# Aviso local somente quando existem novidades ou um problema novo.
# Nunca inclui dados de sessão; execuções sem mudanças ficam silenciosas.
try {
    $reportFile = Join-Path $projectDirectory 'private\last-sync.json'
    $report = Get-Content -LiteralPath $reportFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $notificationFile = Join-Path $privateDirectory 'last-notification.json'
    $newItems = [int]$report.summary.uploaded + [int]$report.summary.reconciled + [int]$report.summary.uploaded_ocr + [int]$report.summary.uploaded_image
    $message = $null
    if ($report.status -eq 'attention_required') {
        $fingerprint = 'attention:' + $report.error_type + ':' + ($report.summary | ConvertTo-Json -Compress)
        $previous = if (Test-Path -LiteralPath $notificationFile) { Get-Content -LiteralPath $notificationFile -Raw | ConvertFrom-Json } else { $null }
        if ($previous.fingerprint -ne $fingerprint) {
            $message = 'A atualizacao precisa de atencao. Abra o relatorio na pasta do projeto. Se a sessao expirou, conecte a conta novamente.'
        }
    } elseif ($newItems -gt 0) {
        $fingerprint = [string]$report.checked_at_utc
        $message = "$newItems materiais foram atualizados nos seus notebooks de estudo."
    }
    if ($message) {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $notice = New-Object System.Windows.Forms.NotifyIcon
        $notice.Icon = [System.Drawing.SystemIcons]::Information
        $notice.Visible = $true
        $notice.BalloonTipTitle = 'Materiais de estudo'
        $notice.BalloonTipText = $message
        $notice.ShowBalloonTip(8000)
        Start-Sleep -Seconds 9
        $notice.Dispose()
        @{ fingerprint=$fingerprint; shown_at=(Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $notificationFile -Encoding UTF8
    } elseif ($report.status -eq 'ok') {
        @{ fingerprint='ok' } | ConvertTo-Json | Set-Content -LiteralPath $notificationFile -Encoding UTF8
    }
} catch {
    # Notificacoes nao alteram o resultado da sincronizacao.
}
exit $syncExitCode
