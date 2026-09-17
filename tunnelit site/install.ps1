$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Tunnel It Installer            " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Detecting Python..."
$pythonPath = ""
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonPath = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonPath = "py"
} else {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

$versionString = & $pythonPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$versionSplit = $versionString -split "\."
$major = [int]$versionSplit[0]
$minor = [int]$versionSplit[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
    Write-Host "Error: Python 3.9 or newer is required. Found $versionString" -ForegroundColor Red
    exit 1
}
Write-Host "Found Python $versionString" -ForegroundColor Green

Write-Host "Installing Tunnel It CLI from GitHub..."
Invoke-Expression "$pythonPath -m pip install --user `"git+https://github.com/Mohd-Alyan/TunnelIT-main.git#subdirectory=tunnelit cli`""
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Installation failed." -ForegroundColor Red
    exit 1
}

# Find where Python placed the executable
$scriptsPath = & $pythonPath -c "import os, sysconfig; print(sysconfig.get_path('scripts', f'{os.name}_user'))"

# Read actual registry PATH variables
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$machinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
$combinedPath = "$userPath;$machinePath"

# If it's missing from both User and System PATH, update the User PATH in registry
if ($combinedPath -notmatch [regex]::Escape($scriptsPath)) {
    Write-Host "Adding Python scripts directory ($scriptsPath) to your PATH..." -ForegroundColor Cyan
    $newUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $scriptsPath } else { "$userPath;$scriptsPath" }
    [Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")
    Write-Host "Successfully updated your Windows Environment Variables!" -ForegroundColor Green
    Write-Host "IMPORTANT: You MUST close and restart your terminal for the permanent change to apply." -ForegroundColor Yellow
}

# Update the current session PATH so it works immediately
$env:PATH = "$($env:PATH);$scriptsPath"

Write-Host "Verifying installation..."
try {
    & "$scriptsPath\tunnel-it.exe" --help > $null
    Write-Host "Verification successful!" -ForegroundColor Green
} catch {
    Write-Host "Warning: Verification failed. Could not execute $scriptsPath\tunnel-it.exe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "           Ready to tunnel!             " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Wake the default relay:   tunnel-it wakeup"
Write-Host "2. Expose a local service:   tunnel-it expose 5000"
Write-Host ""
Write-Host "To see all commands, run:    tunnel-it --help"
Write-Host "========================================" -ForegroundColor Cyan
