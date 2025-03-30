@echo off
echo Creating directory structure for YouTube Shorts Automation...

mkdir config 2>nul
mkdir data\content_db\general 2>nul
mkdir data\assets\audio 2>nul
mkdir data\assets\images 2>nul
mkdir data\assets\video 2>nul
mkdir data\output_tracking 2>nul
mkdir logs 2>nul
mkdir gui\monitoring 2>nul
mkdir core 2>nul
mkdir utils 2>nul

echo Creating template directories...
mkdir template 2>nul

echo Copying default configuration files...
copy config\config.yaml template\config.yaml 2>nul
copy config\api_keys.yaml template\api_keys.yaml 2>nul

echo Directory structure setup complete.
echo.
echo Next steps:
echo 1. Edit config\config.yaml to customize settings
echo 2. Edit config\api_keys.yaml to add your API keys
echo 3. Run the application with: python main.py
echo.
echo Done!