<#
.SYNOPSIS
Installs the Tunnel It CLI.

.DESCRIPTION
This script detects Python, checks its version, and installs the Tunnel It CLI directly from GitHub.
It installs the package for the current user.
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Tunnel It Installer            " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detect Python
Write-Host "Detecting Python..."
$pythonPath = ""
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonPath = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonPath = "py"
} else {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.9 or newer and try again." -ForegroundColor Red
    exit 1
}

# 2. Verify Python version
$versionString = & $pythonPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$versionSplit = $versionString -split "\."
$major = [int]$versionSplit[0]
$minor = [int]$versionSplit[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
    Write-Host "Error: Python 3.9 or newer is required." -ForegroundColor Red
    Write-Host "Found Python $versionString" -ForegroundColor Red
    exit 1
}

Write-Host "Found Python $versionString" -ForegroundColor Green
Write-Host ""

# 3. Install Tunnel It
Write-Host "Installing Tunnel It CLI from GitHub..."
$installCommand = "$pythonPath -m pip install --user `"git+https://github.com/Mohd-Alyan/TunnelIT-main.git#subdirectory=tunnelit cli`""
Invoke-Expression $installCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Installation failed." -ForegroundColor Red
    exit 1
}

Write-Host "Installation completed." -ForegroundColor Green
Write-Host ""

# Check if Scripts directory is in PATH
$scriptsPath = ""
if ($IsWindows) {
    # We ask Python for the user scripts directory using sysconfig which correctly handles Windows Store Python
    $scriptsPath = & $pythonPath -c "import os, sysconfig; print(sysconfig.get_path('scripts', f'{os.name}_user'))"
    
    $envPath = [Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($envPath -notmatch [regex]::Escape($scriptsPath)) {
        Write-Host "Warning: The Python user scripts directory is not in your PATH." -ForegroundColor Yellow
        Write-Host "Automatically adding it to your User Environment Variables..." -ForegroundColor Cyan
        
        # Add to permanent user PATH
        $currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        $newUserPath = if ($currentUserPath) { "$currentUserPath;$scriptsPath" } else { $scriptsPath }
        [Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")
        
        Write-Host "Success! The path has been added permanently." -ForegroundColor Green
        Write-Host "IMPORTANT: You MUST restart your PowerShell terminal for the changes to take effect." -ForegroundColor Yellow
        Write-Host ""
    }
}

# Verify installation
Write-Host "Verifying installation..."
$tunnelItCmd = if ($scriptsPath -and (Test-Path "$scriptsPath\tunnel-it.exe")) { "$scriptsPath\tunnel-it.exe" } else { "tunnel-it" }

try {
    & $tunnelItCmd --help > $null
    Write-Host "Verification successful!" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not automatically verify 'tunnel-it' command. Ensure the Python scripts directory is in your PATH." -ForegroundColor Yellow
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
