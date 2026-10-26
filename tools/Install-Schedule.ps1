param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [Parameter(Mandatory=$true)][string]$PrivateHome,
    [ValidatePattern('^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')][string]$DailyAt = '23:00'
)
$ErrorActionPreference = 'Stop'
$projectDirectory = (Resolve-Path -LiteralPath $ProjectRoot).Path
$privateDirectory = (Resolve-Path -LiteralPath $PrivateHome).Path
$scheduledProgram = Join-Path $projectDirectory '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $scheduledProgram)) { throw 'Prepare o ambiente virtual antes de instalar a rotina.' }
$taskName = 'MoodleStudySync-Empreendedorismo'
$taskDescription = 'Meus Estudos: atualiza as materias ativas do Moodle nos notebooks Google, diariamente as ' + $DailyAt + '.'
$previous = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($previous -and -not ($previous.Actions.Arguments -like ('*' + $projectDirectory + '*'))) {
    throw 'Ja existe uma tarefa com esse nome que nao pertence a este projeto.'
}
$action = New-ScheduledTaskAction -Execute $scheduledProgram -Argument '-m moodle_study_sync.scheduled' -WorkingDirectory $projectDirectory
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $taskDescription
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Select-Object TaskName, State
@{ private_home=$privateDirectory; task_name=$taskName; daily_at=$DailyAt } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectDirectory 'private\runtime.local.json') -Encoding UTF8
