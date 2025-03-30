# YouTube Shorts Automation System Runner Script
Write-Host "Starting YouTube Shorts Automation System..." -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Python is not installed or not in PATH. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists, create if not
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    try {
        python -m venv venv
        Write-Host "Virtual environment created." -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to create virtual environment. Please check your Python installation." -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
try {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
}
catch {
    Write-Host "Failed to activate virtual environment." -ForegroundColor Red
    exit 1
}

# Check if dependencies are installed, install if not
if (-not (Test-Path "venv\Lib\site-packages\PyQt5")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    try {
        pip install -r requirements.txt
        Write-Host "Dependencies installed." -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to install dependencies. Please check requirements.txt." -ForegroundColor Red
        exit 1
    }
}

# Create necessary directories if they don't exist
$directories = @(
    "config",
    "data\content_db\general",
    "data\assets\audio",
    "data\assets\images",
    "data\assets\video",
    "data\output_tracking",
    "logs",
    "gui\monitoring"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "Creating directory: $dir" -ForegroundColor Yellow
        New-Item -Path $dir -ItemType Directory | Out-Null
    }
}

# Create default config files if they don't exist
if (-not (Test-Path "config\config.yaml")) {
    Write-Host "Creating default config file..." -ForegroundColor Yellow
    try {
        if (Test-Path "template\config.yaml") {
            Copy-Item "template\config.yaml" -Destination "config\config.yaml"
        }
        else {
            Write-Host "WARNING: template\config.yaml not found. You'll need to create config.yaml manually." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "WARNING: Could not create default config file. You'll need to create it manually." -ForegroundColor Yellow
    }
}

if (-not (Test-Path "config\api_keys.yaml")) {
    Write-Host "Creating API keys template..." -ForegroundColor Yellow
    try {
        if (Test-Path "template\api_keys.yaml") {
            Copy-Item "template\api_keys.yaml" -Destination "config\api_keys.yaml"
        }
        else {
            Write-Host "WARNING: template\api_keys.yaml not found. You'll need to create api_keys.yaml manually." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "WARNING: Could not create API keys template. You'll need to create it manually." -ForegroundColor Yellow
    }
}

# Run the application
Write-Host "Starting application..." -ForegroundColor Green
python main.py $args

# Deactivate virtual environment
try {
    Write-Host "Deactivating virtual environment..." -ForegroundColor Yellow
    deactivate
}
catch {
    # Silently ignore deactivation errors
}

Write-Host "Done." -ForegroundColor Cyan