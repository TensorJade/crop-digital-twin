param([switch]$Once)
. "$PSScriptRoot\common.ps1"
$uvExecutable = Get-WorkspaceUv
Push-Location $script:WorkspaceRoot
try {
    $workerArguments = @('run', '--locked', '--no-sync', 'python', 'scripts/simulation_worker.py')
    if ($Once) { $workerArguments += '--once' }
    Invoke-Checked $uvExecutable $workerArguments
} finally { Pop-Location }
