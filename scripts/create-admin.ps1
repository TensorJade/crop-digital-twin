param(
    [Parameter(Mandatory=$true)][string]$Username,
    [Parameter(Mandatory=$true)][string]$DisplayName,
    [Parameter(Mandatory=$true)][string]$Organization,
    [switch]$AdoptLegacy
)
. "$PSScriptRoot\common.ps1"
Push-Location $script:WorkspaceRoot
try {
    $adminArguments = @('run', '--locked', '--no-sync', 'python', 'scripts/create_admin.py',
        '--username', $Username, '--display-name', $DisplayName, '--organization', $Organization)
    if ($AdoptLegacy) { $adminArguments += '--adopt-legacy' }
    Invoke-Checked (Get-WorkspaceUv) $adminArguments
} finally { Pop-Location }
