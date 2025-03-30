"""
Configure MoviePy to use the correct FFmpeg binary
"""
import os
from moviepy.config import change_settings

def configure_ffmpeg():
    """Configure MoviePy to use the correct FFmpeg path"""
    ffmpeg_path = os.environ.get('FFMPEG_BINARY', 'C:\\ffmpeg\\bin\\ffmpeg.exe')
    ffprobe_path = os.environ.get('FFPROBE_BINARY', 'C:\\ffmpeg\\bin\\ffprobe.exe')
    
    # Ensure the paths exists
    if not os.path.exists(ffmpeg_path):
        print(f"Warning: FFmpeg not found at {ffmpeg_path}")
    
    if not os.path.exists(ffprobe_path):
        print(f"Warning: FFprobe not found at {ffprobe_path}")
    
    # Set the paths in MoviePy's configuration
    change_settings({
        "FFMPEG_BINARY": ffmpeg_path,
        "FFPROBE_BINARY": ffprobe_path
    })
    
    print(f"MoviePy configured to use FFmpeg at: {ffmpeg_path}")
    print(f"MoviePy configured to use FFprobe at: {ffprobe_path}")