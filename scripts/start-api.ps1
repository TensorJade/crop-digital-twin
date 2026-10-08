. "$PSScriptRoot\common.ps1"
$uvExecutable = Get-WorkspaceUv
Push-Location $script:WorkspaceRoot
try {
    $serverArguments = @('run', '--locked', '--no-sync', 'uvicorn', 'crop_twin.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload')
    if (Test-Path -LiteralPath '.env') { $serverArguments += @('--env-file', '.env') }
    Invoke-Checked $uvExecutable $serverArguments
} finally { Pop-Location }
