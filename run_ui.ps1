$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

if (Test-Path -LiteralPath $bundledPython) {
    $pythonExe = $bundledPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw 'Python 3.10 or newer was not found. Install Python, then run this script again.'
    }
    $pythonExe = $pythonCommand.Source
}

Push-Location -LiteralPath $projectDir
try {
    & $pythonExe .\app.py @args
} finally {
    Pop-Location
}
