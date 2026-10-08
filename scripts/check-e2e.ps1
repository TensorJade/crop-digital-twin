param([string]$NodeBinDirectory = '', [string]$BrowserChannel = '')
. "$PSScriptRoot\common.ps1"
Set-WorkspaceNode -NodeBinDirectory $NodeBinDirectory
$previousChannel = $env:CROP_TWIN_TEST_BROWSER
if ($BrowserChannel) { $env:CROP_TWIN_TEST_BROWSER = $BrowserChannel }
Push-Location (Join-Path $script:WorkspaceRoot 'frontend')
try { Invoke-WorkspaceNpm @('run', 'test:e2e') }
finally { Pop-Location; $env:CROP_TWIN_TEST_BROWSER = $previousChannel }
