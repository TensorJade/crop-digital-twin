param(
    [Parameter(Mandatory = $true)][string]$Slug,
    [Parameter(Mandatory = $true)][string]$Author
)
. "$PSScriptRoot\common.ps1"
if ($Slug -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') { throw 'Slug must use lowercase letters, digits and hyphens.' }
$logDate = Get-Date -Format 'yyyy-MM-dd'
$logPath = Join-Path $script:WorkspaceRoot "docs\dev-log\$logDate-$Slug.md"
if (Test-Path -LiteralPath $logPath) { throw "Log already exists: $logPath" }
$logText = Get-Content -LiteralPath (Join-Path $script:WorkspaceRoot 'docs\templates\dev-log.md') -Raw -Encoding UTF8
$logText = $logText.Replace('{{date}}', $logDate).Replace('{{author}}', $Author).Replace('{{slug}}', $Slug)
[System.IO.File]::WriteAllText($logPath, $logText, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Created $logPath. Fill in actual work and evidence."
