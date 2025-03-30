@echo off
echo Starting YouTube Shorts Automation System...

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist venv\ (
    echo Creating virtual environment...
    python -m venv venv
    
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment. Please check your Python installation.
        exit /b 1
    )
    
    echo Virtual environment created.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed, install if not
if not exist venv\Lib\site-packages\PyQt5 (
    echo Installing dependencies...
    pip install -r requirements.txt
    
    if %errorlevel% neq 0 (
        echo Failed to install dependencies. Please check requirements.txt.
        exit /b 1
    )
    
    echo Dependencies installed.
)

REM Create necessary directories if they don't exist
if not exist config\ mkdir config
if not exist data\content_db\general mkdir data\content_db\general
if not exist data\assets\audio mkdir data\assets\audio
if not exist data\assets\images mkdir data\assets\images
if not exist data\assets\video mkdir data\assets\video
if not exist data\output_tracking mkdir data\output_tracking
if not exist logs mkdir logs
if not exist gui\monitoring mkdir gui\monitoring

REM Create default config files if they don't exist
if not exist config\config.yaml (
    echo Creating default config file...
    copy template\config.yaml config\config.yaml > nul 2>&1
    if not exist config\config.yaml (
        echo WARNING: Could not create default config file. You'll need to create it manually.
    )
)

if not exist config\api_keys.yaml (
    echo Creating API keys template...
    copy template\api_keys.yaml config\api_keys.yaml > nul 2>&1
    if not exist config\api_keys.yaml (
        echo WARNING: Could not create API keys template. You'll need to create it manually.
    )
)

REM Run the application
echo Starting application...
python main.py %*

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo Done.