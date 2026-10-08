param([string]$NodeBinDirectory = '')
. "$PSScriptRoot\common.ps1"
Set-WorkspaceNode -NodeBinDirectory $NodeBinDirectory
$uvExecutable = Get-WorkspaceUv
Push-Location $script:WorkspaceRoot
try {
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'ruff', 'check', 'backend', 'packages', 'scripts')
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'ruff', 'format', '--check', 'backend', 'packages', 'scripts')
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'mypy')
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'pytest', '--cov=crop_twin', '--cov-report=term-missing', '--cov-fail-under=80')
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'python', 'scripts/export_openapi.py', '--check')
    Invoke-Checked $uvExecutable @('run', '--locked', '--no-sync', 'python', 'scripts/check_workspace.py')
    Push-Location 'frontend'
    try {
        foreach ($checkName in @('typecheck', 'lint', 'format:check', 'test', 'build')) {
            Invoke-WorkspaceNpm @('run', $checkName)
        }
    } finally { Pop-Location }
    Write-Host 'Local checks passed, including isolated SQLite integration. PostgreSQL requires its test URL; crop accuracy is evaluated separately.'
} finally { Pop-Location }
