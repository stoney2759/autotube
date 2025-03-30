# YouTube Shorts Automation System

A fully automated system for generating and uploading YouTube Shorts content without human intervention after initial setup. The system features a visual workflow interface showing the active processes and handles the entire content creation pipeline: generating ideas, creating images, producing videos, adding audio, and uploading to YouTube.

## Features

- **Automated Content Creation**: Generate compelling video content from templates and themes
- **Image Generation**: Connect to image generation APIs to create visual content
- **Video Assembly**: Combine images with transitions and effects
- **Audio Integration**: Add background music and optional voiceovers
- **YouTube Upload**: Automatically upload and schedule videos to YouTube
- **Visual Workflow**: Monitor and control the entire process through a graphical interface
- **Scheduling**: Set up recurring content generation on custom intervals

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (optional, for version control)

### Setup Instructions

1. **Clone or download the repository**:
   ```
   git clone https://github.com/yourusername/youtube-shorts-automation.git
   cd youtube-shorts-automation
   ```

2. **Create and activate a virtual environment (recommended)**:
   ```powershell
   # On Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # On Windows (CMD)
   python -m venv venv
   venv\Scripts\activate.bat
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Create directory structure**:
   ```powershell
   mkdir -p config
   mkdir -p data/content_db/general
   mkdir -p data/assets/audio
   mkdir -p data/assets/images
   mkdir -p data/assets/video
   mkdir -p data/output_tracking
   mkdir -p logs
   mkdir -p gui/monitoring
   ```

5. **Configure your API keys**:
   Edit the `config/api_keys.yaml` file to add your YouTube API credentials and any image generation API keys you want to use.

## Running the Application

1. **Start the GUI application**:
   ```
   python main.py
   ```

2. **Run in headless mode** (no GUI, for servers):
   ```
   python main.py --headless
   ```

3. **Run a single workflow and exit**:
   ```
   python main.py --headless --run-once --theme "travel"
   ```

## Usage Guide

1. **Initial Setup**:
   - Configure your API keys in `config/api_keys.yaml`
   - Customize settings in `config/config.yaml`
   - Create content templates in `data/content_db`

2. **Running Workflows**:
   - Use the control panel to set the content theme and interval
   - Click "Start Workflow" to begin automated content generation
   - Monitor progress in the workflow visualization panel
   - View logs in the log viewer panel

3. **Managing Content**:
   - Generated videos are stored in `data/assets/video`
   - Upload records are kept in `data/output_tracking`

## Configuration

### Main Configuration (`config/config.yaml`)

The main configuration file controls all aspects of the system, including:
- Workflow scheduling
- Content generation parameters
- Video and image settings
- Audio preferences
- YouTube upload settings

### API Keys (`config/api_keys.yaml`)

This file stores your API credentials for:
- YouTube API (for uploads)
- Image generation APIs (Stable Diffusion, DALL-E, etc.)
- Audio APIs

### Content Templates (`data/content_db/`)

JSON files containing templates for content generation, including:
- Title templates
- Description templates
- Image prompt ideas
- Keywords and tags

## Troubleshooting

- **API Connection Issues**: Check your internet connection and verify API keys in `config/api_keys.yaml`
- **Module Import Errors**: Ensure your virtual environment is activated and all dependencies are installed
- **GUI Issues**: Run with `--debug` flag for more detailed logging: `python main.py --debug`

## License

[MIT License](LICENSE)

## Acknowledgments

- This project uses various open-source libraries listed in `requirements.txt`
- Special thanks to the PyQt team for the GUI framework