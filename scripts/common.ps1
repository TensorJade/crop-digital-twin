Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:WorkspaceRoot = Split-Path -Parent $PSScriptRoot

function Set-WorkspaceNode {
    param([string]$NodeBinDirectory = '')
    $localSettingsPath = Join-Path $script:WorkspaceRoot '.tools\local-settings.json'
    if (-not $NodeBinDirectory -and (Test-Path -LiteralPath $localSettingsPath)) {
        $localSettings = Get-Content -LiteralPath $localSettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $NodeBinDirectory = $localSettings.nodeBinDirectory
    }
    if ($NodeBinDirectory) {
        $resolvedNodeBin = (Resolve-Path -LiteralPath $NodeBinDirectory).Path
        if (-not (Test-Path -LiteralPath (Join-Path $resolvedNodeBin 'node.exe'))) {
            throw 'The specified directory must contain node.exe.'
        }
        $env:PATH = "$resolvedNodeBin;$env:PATH"
    }
    $nodeVersionText = & node --version
    if ($LASTEXITCODE -ne 0) { throw 'Node.js is unavailable.' }
    $nodeVersion = [version]$nodeVersionText.TrimStart('v')
    $isSupported = (($nodeVersion.Major -eq 22 -and $nodeVersion -ge [version]'22.18.0') -or $nodeVersion -ge [version]'24.12.0')
    if (-not $isSupported) {
        throw "Unsupported Node $nodeVersionText. Use Node 24.19.0 or pass -NodeBinDirectory."
    }
}

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

function Get-WorkspaceUv {
    $uvExecutable = Join-Path $script:WorkspaceRoot '.tools\uv\Scripts\uv.exe'
    if (-not (Test-Path -LiteralPath $uvExecutable)) {
        throw 'Run scripts\bootstrap.ps1 first.'
    }
    return $uvExecutable
}

function Invoke-WorkspaceNpm {
    param([string[]]$Arguments)
    # npm.cmd may prefer a different node.exe beside itself on Windows.
    $nodeExecutable = (Get-Command node.exe -ErrorAction Stop).Source
    $npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source
    $npmCli = Join-Path (Split-Path -Parent $npmCommand) 'node_modules\npm\bin\npm-cli.js'
    if (-not (Test-Path -LiteralPath $npmCli)) {
        throw 'Cannot locate npm CLI next to npm.cmd. Install npm with Node.js.'
    }
    Invoke-Checked -FilePath $nodeExecutable -Arguments (@($npmCli) + $Arguments)
}
