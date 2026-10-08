param([string]$NodeBinDirectory = '')
. "$PSScriptRoot\common.ps1"
Set-WorkspaceNode -NodeBinDirectory $NodeBinDirectory
Push-Location (Join-Path $script:WorkspaceRoot 'frontend')
try { Invoke-WorkspaceNpm @('run', 'dev') } finally { Pop-Location }
