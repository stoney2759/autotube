# YouTube Shorts Automation System Setup Script
Write-Host "Creating directory structure for YouTube Shorts Automation..." -ForegroundColor Cyan

# Create directory structure
$directories = @(
    "config",
    "data\content_db\general",
    "data\assets\audio",
    "data\assets\images",
    "data\assets\video",
    "data\output_tracking",
    "logs",
    "gui\monitoring",
    "core",
    "utils",
    "template"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "  Creating directory: $dir" -ForegroundColor Yellow
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    } else {
        Write-Host "  Directory already exists: $dir" -ForegroundColor Green
    }
}

# Copy configuration templates if they exist
Write-Host "Checking for configuration files..." -ForegroundColor Cyan

if (Test-Path "config\config.yaml") {
    Write-Host "  Backing up config.yaml to template directory" -ForegroundColor Yellow
    Copy-Item "config\config.yaml" -Destination "template\config.yaml" -Force
}

if (Test-Path "config\api_keys.yaml") {
    Write-Host "  Backing up api_keys.yaml to template directory" -ForegroundColor Yellow
    Copy-Item "config\api_keys.yaml" -Destination "template\api_keys.yaml" -Force
}

Write-Host "Directory structure setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit config\config.yaml to customize settings" -ForegroundColor White
Write-Host "2. Edit config\api_keys.yaml to add your API keys" -ForegroundColor White
Write-Host "3. Run the application with: python main.py" -ForegroundColor White
Write-Host ""
Write-Host "Done!" -ForegroundColor Green