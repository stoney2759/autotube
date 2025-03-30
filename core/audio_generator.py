"""
Audio Generation Module for YouTube Shorts Automation.
Handles audio selection, generation, and processing.
"""
import logging
import os
import yaml
import random
from datetime import datetime
import requests
import json

# Import directly from moviepy (for version 2.1.2+)
from moviepy import AudioFileClip, concatenate_audioclips, AudioArrayClip, afx

class AudioGenerator:
    """
    Generates or selects audio tracks for YouTube Shorts.
    Can use local audio files or generate them using APIs.
    """
    
    def __init__(self, config_path='config/config.yaml', api_keys_path='config/api_keys.yaml'):
        """
        Initialize audio generator with configuration
        
        Args:
            config_path (str): Path to configuration file
            api_keys_path (str): Path to API keys file
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Audio Generator")
        
        # Load configuration
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            self.logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {
                'audio': {
                    'provider': 'local',
                    'duration_seconds': 60,
                    'fade_in_seconds': 1,
                    'fade_out_seconds': 2
                }
            }
            self.logger.warning("Using default audio configuration")
        
        # Load API keys
        self.api_keys = {}
        try:
            if os.path.exists(api_keys_path):
                with open(api_keys_path, 'r') as file:
                    self.api_keys = yaml.safe_load(file)
                self.logger.debug(f"Loaded API keys from {api_keys_path}")
            else:
                self.logger.warning(f"API keys file not found at {api_keys_path}")
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
        
        # Create audio output directory
        self.output_dir = os.path.join('data', 'assets', 'audio')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Make sure the local audio directory exists
        self.local_audio_dir = os.path.join(self.output_dir, 'local')
        os.makedirs(self.local_audio_dir, exist_ok=True)
        
        # Set explicit FFmpeg paths if needed
        self._configure_ffmpeg()
    
    def _configure_ffmpeg(self):
        """Configure FFmpeg paths for MoviePy"""
        from moviepy.config import change_settings
        
        ffmpeg_binary = os.environ.get('FFMPEG_BINARY', 'C:\\ffmpeg\\bin\\ffmpeg.exe')
        ffprobe_binary = os.environ.get('FFPROBE_BINARY', 'C:\\ffmpeg\\bin\\ffprobe.exe')
        
        if os.path.exists(ffmpeg_binary) and os.path.exists(ffprobe_binary):
            change_settings({
                "FFMPEG_BINARY": ffmpeg_binary,
                "FFPROBE_BINARY": ffprobe_binary
            })
            self.logger.info(f"FFmpeg configured with binary at {ffmpeg_binary}")
        else:
            self.logger.warning("FFmpeg binaries not found at expected locations. Using system defaults.")
    
    def generate_audio(self, theme=None, duration=None, output_path=None):
        """
        Generate or select an audio track based on theme
        
        Args:
            theme (str, optional): Theme for audio selection
            duration (float, optional): Desired duration in seconds
            output_path (str, optional): Path to save the audio
            
        Returns:
            str: Path to the generated/selected audio file
        """
        # Get audio configuration
        audio_config = self.config.get('audio', {})
        provider = audio_config.get('provider', 'local')
        
        if duration is None:
            duration = audio_config.get('duration_seconds', 60)
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"audio_{timestamp}.mp3"
            output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            # Choose provider based on configuration
            if provider == 'api':
                self.logger.info(f"Generating audio using API for theme: {theme}")
                audio_path = self._generate_audio_api(theme, duration, output_path)
            else:
                self.logger.info(f"Selecting local audio for theme: {theme}")
                audio_path = self._select_local_audio(theme, duration, output_path)
            
            # Apply audio processing
            if audio_path:
                audio_path = self._process_audio(audio_path, duration, output_path)
            
            return audio_path
        
        except Exception as e:
            self.logger.error(f"Error generating audio: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return self._generate_silence(duration, output_path)
    
    def _select_local_audio(self, theme, duration, output_path):
        """
        Select an audio file from local directory
        
        Args:
            theme (str): Theme for audio selection
            duration (float): Desired duration in seconds
            output_path (str): Path to save the audio
            
        Returns:
            str: Path to the selected audio file
        """
        # Get all audio files
        audio_files = []
        for root, _, files in os.walk(self.local_audio_dir):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    audio_files.append(os.path.join(root, file))
        
        if not audio_files:
            self.logger.warning(f"No audio files found in {self.local_audio_dir}")
            return self._generate_silence(duration, output_path)
        
        # If we have a theme, try to match with folder name
        if theme:
            theme_dir = os.path.join(self.local_audio_dir, theme.lower())
            theme_files = []
            
            if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
                for root, _, files in os.walk(theme_dir):
                    for file in files:
                        if file.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                            theme_files.append(os.path.join(root, file))
            
            # If we found themed files, use those
            if theme_files:
                self.logger.info(f"Found {len(theme_files)} audio files for theme: {theme}")
                audio_file = random.choice(theme_files)
            else:
                self.logger.info(f"No themed audio files found for {theme}, using random")
                audio_file = random.choice(audio_files)
        else:
            # Pick a random file
            audio_file = random.choice(audio_files)
        
        self.logger.info(f"Selected audio file: {audio_file}")
        return audio_file
    
    def _generate_audio_api(self, theme, duration, output_path):
        """
        Generate audio using an API
        
        Args:
            theme (str): Theme for audio generation
            duration (float): Desired duration in seconds
            output_path (str): Path to save the audio
            
        Returns:
            str: Path to the generated audio file
        """
        self.logger.warning("Audio generation API not fully implemented")
        return self._select_local_audio(theme, duration, output_path)
    
    def _process_audio(self, audio_path, target_duration, output_path):
        """
        Process audio file to match desired duration and apply effects
        
        Args:
            audio_path (str): Path to the audio file
            target_duration (float): Desired duration in seconds
            output_path (str): Path to save the processed audio
            
        Returns:
            str: Path to the processed audio file
        """
        try:
            # Get audio configuration
            audio_config = self.config.get('audio', {})
            fade_in = audio_config.get('fade_in_seconds', 1)
            fade_out = audio_config.get('fade_out_seconds', 2)
            
            # Load audio file
            self.logger.info(f"Processing audio file: {audio_path}")
            audio = AudioFileClip(audio_path)
            original_duration = audio.duration
            
            # Apply fade in/out
            if fade_in > 0:
                audio = audio.fx(afx.audio_fadein, fade_in)
            
            if fade_out > 0:
                audio = audio.fx(afx.audio_fadeout, fade_out)
            
            # Handle duration adjustment
            if abs(original_duration - target_duration) > 1:  # If more than 1 second difference
                if original_duration < target_duration:
                    # Audio is too short, loop it
                    self.logger.info(f"Audio is too short ({original_duration}s), looping to {target_duration}s")
                    n_loops = int(target_duration / original_duration) + 1
                    audio = concatenate_audioclips([audio] * n_loops).subclip(0, target_duration)
                else:
                    # Audio is too long, trim it
                    self.logger.info(f"Audio is too long ({original_duration}s), trimming to {target_duration}s")
                    audio = audio.subclip(0, target_duration)
            
            # Write processed audio
            process_path = output_path
            audio.write_audiofile(
                process_path,
                fps=44100,
                nbytes=2,
                codec='libmp3lame',
                bitrate='192k',
                logger=None  # Use internal logger
            )
            
            self.logger.info(f"Audio processed successfully: {process_path}")
            return process_path
            
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return audio_path  # Return original if processing fails
        finally:
            # Clean up resources
            try:
                audio.close() if 'audio' in locals() else None
            except Exception as e:
                self.logger.warning(f"Error cleaning up resources: {e}")
    
    def _generate_silence(self, duration, output_path):
        """
        Generate a silent audio file
        
        Args:
            duration (float): Duration in seconds
            output_path (str): Path to save the silent audio
            
        Returns:
            str: Path to the silent audio file
        """
        try:
            import numpy as np
            
            self.logger.info(f"Generating {duration}s of silence to {output_path}")
            
            # Create a silent audio clip
            sample_rate = 44100
            silence = np.zeros((int(duration * sample_rate), 2), dtype=np.float32)
            silent_clip = AudioArrayClip(silence, fps=sample_rate)
            
            # Save the silent audio
            silent_clip.write_audiofile(
                output_path,
                fps=sample_rate,
                nbytes=2,
                codec='libmp3lame',
                bitrate='192k',
                logger=None  # Use internal logger
            )
            
            self.logger.info(f"Silent audio generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating silent audio: {e}")
            return None