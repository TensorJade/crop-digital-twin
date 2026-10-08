. "$PSScriptRoot\common.ps1"
$uvExecutable = Get-WorkspaceUv
Push-Location $script:WorkspaceRoot
try {
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'python', 'scripts/init_db.py')
} finally { Pop-Location }
