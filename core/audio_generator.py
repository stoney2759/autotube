"""
OpenAI-Powered Audio Generation Module for YouTube Shorts Automation.
Handles AI-generated audio for TTS and background music.
"""
import logging
import os
import yaml
import random
from datetime import datetime
import requests
import json
import io
import time
import subprocess
from typing import Optional, List

# Import from moviepy.editor for version 1.0.3
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip

class AudioGenerator:
    """
    Generates AI-powered audio tracks for YouTube Shorts
    Uses OpenAI services for TTS and background music generation
    """
    
    def __init__(self, config_loader=None, file_manager=None, config_path='config/config.yaml', api_keys_path='config/api_keys.yaml'):
        """
        Initialize audio generator with AI configuration
        
        Args:
            config_loader (ConfigLoader, optional): Configuration loader instance
            file_manager (FileManager, optional): File manager instance
            config_path (str): Path to configuration file
            api_keys_path (str): Path to API keys file
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OpenAI-Powered Audio Generator")
        
        # Load configuration
        try:
            # Check if a ConfigLoader is provided
            if config_loader and hasattr(config_loader, 'get_config_value'):
                self.config = {
                    'audio': {
                        'provider': config_loader.get_config_value('audio.provider', 'tts'),
                        'duration_seconds': config_loader.get_config_value('audio.duration_seconds', 60),
                        'tts_voice': config_loader.get_config_value('audio.tts_voice', 'nova')
                    }
                }
                self.logger.debug("Loaded configuration from ConfigLoader")
            else:
                # Fallback to file-based loading
                with open(config_path, 'r') as file:
                    self.config = yaml.safe_load(file)
                self.logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {
                'audio': {
                    'provider': 'tts',
                    'duration_seconds': 60,
                    'tts_voice': 'nova',
                }
            }
            self.logger.warning("Using default audio configuration")
        
        # Load API keys
        try:
            # Check if a file path is available
            if config_loader and hasattr(config_loader, 'get_api_key'):
                # Use the ConfigLoader's method to get the API key
                self.openai_api_key = config_loader.get_api_key('image_generation') or \
                                      config_loader.get_api_key('audio')
                self.logger.debug("Loaded API key from ConfigLoader")
                self.api_key = self.openai_api_key  # Keep a consistent reference
            else:
                # Fallback to file-based loading
                with open(api_keys_path, 'r') as file:
                    api_keys = yaml.safe_load(file)
                
                # Check different possible key locations
                possible_key_paths = [
                    ['image_generation', 'api_key'],  # First check image generation keys
                    ['audio', 'api_key']              # Then check audio keys
                ]
                
                self.openai_api_key = None
                for path in possible_key_paths:
                    try:
                        current_dict = api_keys
                        for key in path:
                            current_dict = current_dict[key]
                        
                        # Check if the key is not a placeholder
                        if current_dict and current_dict != "YOUR_API_KEY":
                            self.openai_api_key = current_dict
                            self.api_key = self.openai_api_key  # Keep a consistent reference
                            self.logger.info(f"OpenAI API key found via path: {'.'.join(path)}")
                            break
                    except (KeyError, TypeError):
                        continue
                
                # If key is still not found
                if not self.openai_api_key:
                    raise ValueError("No valid OpenAI API key found")
        
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            raise ValueError("OpenAI API key is required for audio generation")
        
        # Create audio output directory
        # Use file manager if provided, otherwise use default path
        try:
            if file_manager and hasattr(file_manager, 'output_dir'):
                self.output_dir = file_manager.output_dir
            else:
                self.output_dir = os.path.join('data', 'assets', 'audio')
            
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating output directory: {e}")
            self.output_dir = os.path.join('data', 'assets', 'audio')
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Final validation
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required for audio generation. " 
                "Please add your API key to api_keys.yaml under image_generation or audio section."
            )
    
    def generate_coherent_script(self, theme: str, duration: int) -> str:
        """
        Generate a coherent script for TTS based on the theme and duration.
        
        Args:
            theme (str): The theme for the script
            duration (int): Target duration in seconds
            
        Returns:
            str: Generated script
        """
        # Approximate word count for the duration (average speaking pace is ~150 words per minute)
        target_word_count = int((duration / 60) * 130)  # Use 130 wpm for a comfortable pace
        
        try:
            # Create a prompt for better script generation
            prompt = f"""Create a short, engaging script for a {duration}-second YouTube Short about {theme}. 
            The script should be concise and focused, with approximately {target_word_count} words.
            Focus on one clear message or tip that viewers can take away.
            Use natural, conversational language with short sentences.
            Do not include visual directions or timestamps.
            The script should flow naturally from start to finish.
            """

            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a professional script writer for short-form video content."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            # Add timeout to prevent hanging
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            script = response.json()['choices'][0]['message']['content'].strip()
            
            # Clean up the script
            script = self._clean_script_for_tts(script)
            
            self.logger.info(f"Generated coherent script with {len(script.split())} words")
            return script
            
        except Exception as e:
            self.logger.error(f"Error generating script: {str(e)}")
            # Fallback to a simple script
            return f"Welcome to this short video about {theme}. Let's explore some interesting aspects of this topic that you might find surprising and useful in your daily life."

    def _clean_script_for_tts(self, script: str) -> str:
        """
        Clean a script to make it more suitable for TTS.
        
        Args:
            script (str): The original script
            
        Returns:
            str: Cleaned script
        """
        import re
        
        # Remove markdown formatting
        script = re.sub(r'\*\*', '', script)
        script = re.sub(r'\*', '', script)
        
        # Remove scene descriptions in brackets
        script = re.sub(r'\[.*?\]', '', script)
        
        # Remove any speaker indicators
        script = re.sub(r'^\s*.*?:\s*', '', script, flags=re.MULTILINE)
        
        # Remove multiple newlines
        script = re.sub(r'\n{2,}', '\n', script)
        
        # Convert newlines to spaces if needed
        script = re.sub(r'\n', ' ', script)
        
        # Remove extra spaces
        script = re.sub(r'\s+', ' ', script).strip()
        
        return script

    def generate_text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """
        Generate text-to-speech audio using OpenAI's TTS API with enhanced quality.
        
        Args:
            text (str): Text to convert to speech
            voice (str): Voice model to use
            
        Returns:
            bytes: Audio data
        """
        try:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Clean the text
            clean_text = self._clean_script_for_tts(text)
            
            payload = {
                "model": "tts-1-hd",  # Use the HD model for better quality
                "input": clean_text,
                "voice": voice,
                "response_format": "mp3",
                "speed": 1.0  # Normal speaking speed
            }
            
            # Add timeout
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # Check for errors
            if response.status_code != 200:
                self.logger.error(f"TTS API Error: {response.status_code} - {response.text}")
                return None
            
            # Return the audio content directly
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating TTS: {str(e)}")
            raise

    def generate_complete_audio(self, project_id=None, script=None, mood="upbeat", duration=None):
        """
        Generate a complete audio track using AI-powered TTS with enhanced quality.
        
        Args:
            project_id (str, optional): Project ID for organization
            script (str, optional): Script for TTS generation
            mood (str): Mood of the audio (upbeat, calm, etc.)
            duration (float, optional): Desired duration in seconds
            
        Returns:
            str: Path to the generated audio file
        """
        # Use duration from config if not provided
        if duration is None:
            duration = self.config.get('audio', {}).get('duration_seconds', 60)
        
        # Log the generation details
        self.logger.info(f"Generating complete audio for project {project_id} with mood: {mood}, duration: {duration}")
        
        try:
            # First, determine if we need a script
            if not script:
                # Generate a coherent script based on theme
                theme = mood if mood not in ["upbeat", "calm", "intense"] else "technology"
                script = self.generate_coherent_script(theme, duration)
                self.logger.info(f"Generated AI script: {script}")
            
            # Select a voice from available options
            voices = ["nova", "alloy", "echo", "onyx", "shimmer"]  # Different voice options
            selected_voice = self.config.get('audio', {}).get('tts_voice', random.choice(voices))
            
            # Generate TTS audio
            tts_audio_data = self.generate_text_to_speech(script, voice=selected_voice)
            if not tts_audio_data:
                raise Exception("Failed to generate TTS audio")
            
            # Save TTS to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tts_path = os.path.join(self.output_dir, f"tts_{mood}_{timestamp}.mp3")
            with open(tts_path, "wb") as audio_file:
                audio_file.write(tts_audio_data)
            
            self.logger.info(f"Generated TTS audio: {tts_path}")
            
            # Try to get background music
            bg_music_path = self._find_local_music(mood)
            if bg_music_path:
                # Mix TTS with background music
                final_audio_path = os.path.join(self.output_dir, f"final_{mood}_{timestamp}.mp3")
                
                # Use FFmpeg to mix the audio with proper volume levels
                try:
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", tts_path,
                        "-i", bg_music_path,
                        "-filter_complex", "[1:a]volume=0.15[bg]; [0:a][bg]amix=inputs=2:duration=longest",
                        "-c:a", "libmp3lame", "-q:a", "4",
                        final_audio_path
                    ]
                    
                    subprocess.run(cmd, check=True, capture_output=True)
                    self.logger.info(f"Mixed TTS with background music: {final_audio_path}")
                    return final_audio_path
                except Exception as e:
                    self.logger.error(f"Error mixing audio with FFmpeg: {str(e)}")
                    # Fall back to TTS only
                    return tts_path
            else:
                self.logger.info("No background music available. Using TTS audio only.")
                return tts_path
                
        except Exception as e:
            self.logger.error(f"Error generating complete audio: {str(e)}")
            # Generate silence as fallback
            return self._generate_silence(duration, 
                os.path.join(self.output_dir, f"fallback_silence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"))
    
    def _generate_ai_script(self, mood, duration, retry=False):
        """
        Generate a script using OpenAI's GPT model
        
        Args:
            mood (str): Mood or theme for the script
            
        Returns:
            str: Generated script
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Adjust prompt based on retry status
        system_prompt = "You are an expert scriptwriter for short-form video content. Create concise, engaging scripts."
        if retry:
            system_prompt += " Focus on creating a universally appealing script with clear, simple language."
        
        prompt = f"Generate a {mood} themed short script for a YouTube Shorts video. " \
                f"The script should be engaging, concise, and suitable for a {duration}-second video. " \
                "Ensure the script can be easily spoken and understood quickly. " \
                "Aim for clarity, emotion, and a memorable message."
        
        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": [
                {
                    "role": "system", 
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 250,
            "temperature": 0.7  # Add some creativity
        }
        
        try:
            # Add timeout to prevent hanging
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            script = response.json()['choices'][0]['message']['content'].strip()
            self.logger.info(f"Generated AI script: {script}")
            return script
        
        except Exception as e:
            self.logger.error(f"Error generating AI script: {e}")
            # Return a generic fallback script
            return f"Exploring the fascinating world of {mood} content. Every moment is an opportunity for growth and inspiration."
    
    def _generate_tts_audio(self, script, mood, duration):
        """
        Generate Text-to-Speech audio using OpenAI's TTS API
        
        Args:
            script (str): Text to convert to speech
            mood (str): Mood of the audio
            duration (float): Desired duration
            
        Returns:
            str: Path to the generated audio file or None if generation fails
        """
        # Remove emojis and complex formatting
        import re
        
        def remove_emojis(text):
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE)
            return emoji_pattern.sub(r'', text)
        
        # Remove markdown and script formatting
        def clean_script(text):
            # Remove markdown formatting
            text = re.sub(r'\*\*', '', text)
            # Remove scene descriptions in square brackets
            text = re.sub(r'\[.*?\]', '', text)
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        # Clean the script
        clean_text = clean_script(remove_emojis(script))
        
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Get TTS voice from config with more options
        voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        voice = self.config.get('audio', {}).get('tts_voice', random.choice(voices))
        
        payload = {
            "model": "tts-1-hd",  # Use HD model for better quality
            "input": clean_text,
            "voice": voice,
            "response_format": "mp3",
            "speed": 1.0  # Normal speaking speed
        }
        
        try:
            # Add timeout
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # More detailed error handling
            if response.status_code != 200:
                self.logger.error(f"TTS API Error: {response.status_code} - {response.text}")
                return None
            
            # Save the audio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"tts_{mood}_{timestamp}.mp3"
            output_path = os.path.join(self.output_dir, output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Verify audio file size and duration
            file_size = os.path.getsize(output_path)
            if file_size < 1000:  # Small file size indicates potential generation failure
                self.logger.warning(f"Generated TTS audio seems too small: {file_size} bytes")
                os.remove(output_path)
                return None
            
            self.logger.info(f"Generated TTS audio: {output_path}")
            return output_path
        
        except Exception as e:
            self.logger.error(f"Error generating TTS audio: {e}")
            return None
    
    def _find_local_music(self, mood):
        """
        Find appropriate background music from local directories
        
        Args:
            mood (str): Mood to match for music selection
            
        Returns:
            str: Path to music file or None if not found
        """
        # Define paths to check for music files
        music_paths = [
            os.path.join(self.output_dir, "music"),
            os.path.join(os.path.dirname(self.output_dir), "music"),
            os.path.join("data", "assets", "music"),
            os.path.join("music")
        ]
        
        # Add mood-specific subdirectories to search
        mood_specific_paths = []
        for path in music_paths:
            mood_specific_paths.append(os.path.join(path, mood.lower()))
        
        # Combine all paths to search
        all_paths = mood_specific_paths + music_paths
        
        # Find music files
        music_files = []
        for path in all_paths:
            if os.path.exists(path) and os.path.isdir(path):
                for file in os.listdir(path):
                    if file.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                        music_files.append(os.path.join(path, file))
        
        # Randomly select a music file if any were found
        if music_files:
            return random.choice(music_files)
        
        return None
    
    def _mix_audio_tracks(self, main_audio_path, bg_audio_path):
        """
        Mix main audio track with background audio track using ffmpeg directly
        
        Args:
            main_audio_path (str): Path to main audio file
            bg_audio_path (str): Path to background audio file
            
        Returns:
            str: Path to the mixed audio file
        """
        # Create output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"mixed_audio_{timestamp}.mp3")
        
        try:
            # First approach: Try using pydub
            try:
                from pydub import AudioSegment
                
                # Load audio tracks
                main_track = AudioSegment.from_file(main_audio_path)
                bg_track = AudioSegment.from_file(bg_audio_path)
                
                # Adjust volumes
                main_track = main_track + 3  # Slightly increase main track volume
                bg_track = bg_track - 10     # Reduce background track volume
                
                # Ensure tracks are the same length
                if len(bg_track) < len(main_track):
                    bg_track = bg_track * (len(main_track) // len(bg_track) + 1)
                bg_track = bg_track[:len(main_track)]
                
                # Mix tracks
                mixed_track = main_track.overlay(bg_track)
                
                # Save mixed audio
                mixed_track.export(output_path, format="mp3")
                
                self.logger.info(f"Mixed audio saved to: {output_path}")
                return output_path
                
            except Exception as e:
                self.logger.warning(f"Pydub mixing failed: {e}. Trying ffmpeg directly.")
                
                # Second approach: Try using ffmpeg directly
                ffmpeg_cmd = [
                    'ffmpeg', '-y',
                    '-i', main_audio_path,
                    '-i', bg_audio_path,
                    '-filter_complex', '[1:a]volume=0.3[bg];[0:a][bg]amix=inputs=2:duration=first',
                    '-codec:a', 'libmp3lame', '-qscale:a', '2',
                    output_path
                ]
                
                subprocess.run(ffmpeg_cmd, check=True, timeout=30)
                self.logger.info(f"Mixed audio saved to: {output_path}")
                return output_path
                
        except Exception as e:
            self.logger.error(f"Error mixing audio tracks: {e}")
            # Fallback to main audio track
            return main_audio_path
    
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
            from scipy.io import wavfile
            
            self.logger.info(f"Generating {duration}s of silence to {output_path}")
            
            # Create a silent audio clip
            sample_rate = 44100
            silence = np.zeros((int(duration * sample_rate), 2), dtype=np.int16)
            
            # Save using scipy
            wavfile.write(output_path.replace('.mp3', '.wav'), sample_rate, silence)
            
            # Convert to MP3 using ffmpeg
            try:
                ffmpeg_cmd = [
                    'ffmpeg', '-y',
                    '-i', output_path.replace('.mp3', '.wav'),
                    '-codec:a', 'libmp3lame',
                    output_path
                ]
                
                subprocess.run(ffmpeg_cmd, check=True, timeout=15)
                
                # Remove temporary WAV file
                if os.path.exists(output_path.replace('.mp3', '.wav')):
                    os.remove(output_path.replace('.mp3', '.wav'))
                    
            except Exception:
                # If MP3 conversion fails, use WAV
                output_path = output_path.replace('.mp3', '.wav')
            
            self.logger.info(f"Silent audio generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating silent audio: {e}")
            return None