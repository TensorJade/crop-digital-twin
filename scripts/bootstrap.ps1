param([string]$NodeBinDirectory = '')
. "$PSScriptRoot\common.ps1"
Set-WorkspaceNode -NodeBinDirectory $NodeBinDirectory
Push-Location $script:WorkspaceRoot
try {
    Invoke-Checked 'python' @('-c', 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 is required"')
    $toolEnvironment = Join-Path $script:WorkspaceRoot '.tools\uv'
    if (-not (Test-Path -LiteralPath (Join-Path $toolEnvironment 'Scripts\uv.exe'))) {
        Invoke-Checked 'python' @('-m', 'venv', $toolEnvironment)
        Invoke-Checked (Join-Path $toolEnvironment 'Scripts\python.exe') @('-m', 'pip', 'install', 'uv==0.12.23')
    }
    $uvExecutable = Get-WorkspaceUv
    Invoke-Checked $uvExecutable @('sync', '--locked', '--all-packages', '--group', 'dev')
    Push-Location 'frontend'
    try { Invoke-WorkspaceNpm @('ci') } finally { Pop-Location }
    Write-Host 'Environment ready. Run init-db.ps1, create-admin.ps1, then start API/frontend in separate terminals; run check.ps1.'
} finally { Pop-Location }
