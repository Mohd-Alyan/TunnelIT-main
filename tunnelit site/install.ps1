$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Tunnel It Installer            " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Test-PythonExecutable {
    param([string]$cmd)
    try {
        # Actually attempt to run python to bypass the Windows Store dummy app trap
        $testRun = & $cmd -c "print('ok')" 2>&1
        if ($LASTEXITCODE -eq 0 -and $testRun -match "ok") {
            return $true
        }
    } catch {
        # Catch exceptions thrown if the alias opens the store or fails
    }
    return $false
}

Write-Host "Detecting Python..."
$pythonPath = ""
if (Test-PythonExecutable "python") {
    $pythonPath = "python"
} elseif (Test-PythonExecutable "py") {
    $pythonPath = "py"
} else {
    Write-Host "Python is not installed. Initiating automatic installation..." -ForegroundColor Yellow
    
    # Disable progress bar to massively speed up Invoke-WebRequest in PowerShell 5.1
    $ProgressPreference = 'SilentlyContinue'
    $installerPath = "$env:TEMP\python-installer.exe"
    
    Write-Host "Downloading Python 3.12.6..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe" -OutFile $installerPath
    
    Write-Host "Installing Python silently (this may take a minute or two)..." -ForegroundColor Cyan
    # InstallAllUsers=0 ensures no admin/UAC prompt is needed
    $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0"
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    
    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Python installation failed with code $($process.ExitCode)." -ForegroundColor Red
        exit 1
    }
    Write-Host "Python installed successfully!" -ForegroundColor Green

    # Refresh current session PATH to pick up the newly installed Python
    $machinePathExpanded = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    $userPathExpanded = [Environment]::GetEnvironmentVariable("PATH", "User")
    $env:PATH = "$userPathExpanded;$machinePathExpanded"

    # Re-verify python path
    if (Test-PythonExecutable "python") {
        $pythonPath = "python"
    } elseif (Test-PythonExecutable "py") {
        $pythonPath = "py"
    } else {
        $fallbackPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
        if (Test-Path $fallbackPath -and (Test-PythonExecutable $fallbackPath)) {
            $pythonPath = $fallbackPath
        } else {
            Write-Host "Error: Python was installed but couldn't be located. Please restart your terminal and run the script again." -ForegroundColor Red
            exit 1
        }
    }
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

# Check if we are inside a virtual environment
$isVenv = & $pythonPath -c "import sys; print(sys.prefix != sys.base_prefix)"

Write-Host "Installing Tunnel It CLI from GitHub..."
if ($isVenv -eq "True") {
    Write-Host "Virtual environment detected. Installing directly into venv..." -ForegroundColor Cyan
    & $pythonPath -m pip install "git+https://github.com/Mohd-Alyan/TunnelIT-main.git#subdirectory=tunnelit cli"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Installation failed." -ForegroundColor Red
        exit 1
    }
    $scriptsPath = & $pythonPath -c "import sysconfig; print(sysconfig.get_path('scripts'))"
} else {
    & $pythonPath -m pip install --user "git+https://github.com/Mohd-Alyan/TunnelIT-main.git#subdirectory=tunnelit cli"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Installation failed." -ForegroundColor Red
        exit 1
    }
    $scriptsPath = & $pythonPath -c "import os, sysconfig; print(sysconfig.get_path('scripts', f'{os.name}_user'))"
}

if ($isVenv -ne "True") {
    # Read actual registry PATH variables, preserving REG_EXPAND_SZ where applicable
    $userEnv = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
    if ($userEnv) {
        try {
            $userPathRaw = $userEnv.GetValue("PATH", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            $regType = $userEnv.GetValueKind("PATH")
        } catch {
            $userPathRaw = ""
            $regType = [Microsoft.Win32.RegistryValueKind]::ExpandString
        }
        
        $machinePathExpanded = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        $userPathExpanded = [Environment]::GetEnvironmentVariable("PATH", "User")
        $combinedPath = "$userPathExpanded;$machinePathExpanded"

        # Normalize paths for accurate matching (split by ; and remove trailing slashes)
        $pathDirs = $combinedPath -split ';' | ForEach-Object { $_.TrimEnd('\') }
        $normalizedScriptsPath = $scriptsPath.TrimEnd('\')

        # If it's missing from both User and System PATH, update the User PATH in registry
        if ($pathDirs -notcontains $normalizedScriptsPath) {
            Write-Host "Adding Python scripts directory ($scriptsPath) to your PATH..." -ForegroundColor Cyan
            $newUserPathRaw = if ([string]::IsNullOrWhiteSpace($userPathRaw)) { $scriptsPath } else { "$userPathRaw;$scriptsPath" }
            $userEnv.SetValue("PATH", $newUserPathRaw, $regType)
            Write-Host "Successfully updated your Windows Environment Variables!" -ForegroundColor Green
            Write-Host "IMPORTANT: You MUST close and restart your terminal for the permanent change to apply." -ForegroundColor Yellow
        }
    }
}

# Update the current session PATH so it works immediately
$env:PATH = "$($env:PATH);$scriptsPath"

Write-Host "Verifying installation..."
try {
    & "$scriptsPath\tunnel-it.exe" --help > $null
    if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
        Write-Host "Verification successful!" -ForegroundColor Green
    } else {
        Write-Host "Warning: Verification returned exit code $LASTEXITCODE." -ForegroundColor Yellow
    }
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
