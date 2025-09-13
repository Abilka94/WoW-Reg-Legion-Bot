# PowerShell script to set up a virtual environment and run the test suite
param(
    [ValidateSet('all','unit','integration','security','performance')]
    [string]$Suite = 'all',

    # Skip dependency installation (use existing venv as-is)
    [switch]$NoInstall,

    # Run tests in parallel using pytest-xdist (if installed)
    [switch]$UseXdist,

    # Additional arguments passed to pytest (string, e.g. "-k validators -x")
    [string]$ExtraArgs = ''
)

$ErrorActionPreference = 'Stop'

function Invoke-CommandChecked {
    param(
        [Parameter(Mandatory=$true)][string]$Command,
        [string[]]$Args
    )
    Write-Host "-> $Command $($Args -join ' ')" -ForegroundColor DarkGray
    & $Command @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Args -join ' ') (exit $LASTEXITCODE)"
    }
}

# Resolve repo root (one level up from this script)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir '..')
Set-Location $Root

Write-Host "Working directory: $Root" -ForegroundColor Cyan

# Ensure Python is available
try {
    $pyVersion = (& python --version) 2>$null
    Write-Host "Python: $pyVersion" -ForegroundColor Cyan
} catch {
    Write-Error 'Python not found in PATH. Install Python 3.11+.'
    exit 1
}

# Prepare virtual environment
$VenvPath = Join-Path $Root '.venv'
$ActivateScript = Join-Path $VenvPath 'Scripts/Activate.ps1'

if (-not (Test-Path $VenvPath)) {
    Write-Host 'Creating virtual environment (.venv)...' -ForegroundColor Yellow
    Invoke-CommandChecked -Command python -Args @('-m','venv','.venv')
}

# Activate venv
Write-Host 'Activating virtual environment...' -ForegroundColor Yellow
. $ActivateScript

# Upgrade pip/setuptools/wheel
Invoke-CommandChecked -Command python -Args @('-m','pip','install','--upgrade','pip','setuptools','wheel')

if (-not $NoInstall) {
    # Install dependencies
    if (Test-Path 'requirements.txt') {
        Write-Host 'Installing dependencies (requirements.txt)...' -ForegroundColor Yellow
        Invoke-CommandChecked -Command python -Args @('-m','pip','install','-r','requirements.txt')
    }
    if (Test-Path 'requirements-test.txt') {
        Write-Host 'Installing test dependencies (requirements-test.txt)...' -ForegroundColor Yellow
        Invoke-CommandChecked -Command python -Args @('-m','pip','install','-r','requirements-test.txt')
    }
}

# Ensure reports directory exists
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'reports') | Out-Null

# Build pytest arguments
$pytestPath = 'tests/'
switch ($Suite) {
    'unit' { $pytestPath = 'tests/unit/' }
    'integration' { $pytestPath = 'tests/integration/' }
    'security' { $pytestPath = 'tests/security/' }
    'performance' { $pytestPath = 'tests/performance/' }
    default { $pytestPath = 'tests/' }
}

$args = @($pytestPath, '-v', '--tb=short', '-p', 'no:postgresql')
if ($Suite -eq 'performance') {
    $args += @('-m','performance')
}
if ($UseXdist) {
    $args += @('-n','auto')
}

if ($ExtraArgs -and $ExtraArgs.Trim().Length -gt 0) {
    # Simple split. For complex cases, pass args directly via the command line.
    $args += ($ExtraArgs -split ' ')
}

Write-Host "Running pytest ($Suite) ..." -ForegroundColor Green
& python -m pytest @args
exit $LASTEXITCODE

