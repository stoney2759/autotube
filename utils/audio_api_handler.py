"""
Audio API handler for YouTube Shorts Automation System.
Handles text-to-speech and background music generation.
"""
import logging
import io
import os
import time
from typing import Dict, Any, Optional, List
import requests
from utils.error_handling import APIError, retry

logger = logging.getLogger(__name__)

class AudioAPIHandler:
    """Handler for audio generation and selection APIs."""
    
    def __init__(
        self, 
        provider: str = "tts", 
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """
        Initialize the audio API handler.
        
        Args:
            provider: The audio provider (tts, music, etc.)
            api_key: API key for the provider
            api_base: Base URL for the API
        """
        self.api_key = api_key
        self.provider = provider.lower()
        self.api_base = api_base
        self.session = requests.Session()
        
        logger.info(f"Initialized audio API handler for provider: {self.provider}")
    
    def generate_tts(
        self, 
        text: str, 
        voice: str = "en-US-Standard-D",
        language_code: str = "en-US",
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> bytes:
        """
        Generate text-to-speech audio.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID
            language_code: Language code
            speaking_rate: Speed of speech (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            
        Returns:
            Audio data as bytes
            
        Raises:
            APIError: If the audio generation fails
        """
        if self.provider == "tts":
            # Use Google Text-to-Speech for simplicity
            try:
                from gtts import gTTS
                
                logger.info(f"Generating TTS audio for text: {text[:50]}...")
                
                # Convert speaking_rate to gtts format (can only be slow or fast)
                slow = speaking_rate < 0.9
                
                # Create gTTS object
                tts = gTTS(text=text, lang=language_code[:2], slow=slow)
                
                # Save to bytes IO
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                audio_io.seek(0)
                
                logger.info("TTS audio generated successfully")
                return audio_io.read()
            except Exception as e:
                logger.error(f"Error generating TTS audio: {str(e)}")
                raise APIError(f"Error generating TTS audio: {str(e)}") from e
        elif self.provider == "google_cloud_tts" and self.api_key:
            # For a more advanced implementation with Google Cloud TTS
            # This requires setting up a Google Cloud project with TTS API enabled
            return self._generate_google_cloud_tts(
                text, voice, language_code, speaking_rate, pitch
            )
        else:
            raise APIError(f"Unsupported TTS provider: {self.provider}")
    
    def _generate_google_cloud_tts(
        self,
        text: str,
        voice: str,
        language_code: str,
        speaking_rate: float,
        pitch: float
    ) -> bytes:
        """
        Generate TTS using Google Cloud Text-to-Speech API.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID
            language_code: Language code
            speaking_rate: Speed of speech (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            
        Returns:
            Audio data as bytes
        """
        url = f"{self.api_base}/v1/text:synthesize"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": {
                "text": text
            },
            "voice": {
                "languageCode": language_code,
                "name": voice
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": speaking_rate,
                "pitch": pitch
            }
        }
        
        try:
            response = self._make_request(
                method="POST",
                url=url,
                json_data=payload,
                headers=headers
            )
            
            result = response.json()
            
            if "audioContent" not in result:
                logger.error(f"Unexpected response format: {result}")
                raise APIError("Unexpected response from Google Cloud TTS API")
            
            import base64
            audio_data = base64.b64decode(result["audioContent"])
            
            logger.info("TTS audio generated successfully via Google Cloud")
            return audio_data
        except Exception as e:
            logger.error(f"Error generating Google Cloud TTS audio: {str(e)}")
            raise APIError(f"Error generating TTS audio: {str(e)}") from e
    
    def get_background_music(
        self, 
        mood: str = "upbeat", 
        duration_seconds: int = 60
    ) -> bytes:
        """
        Get background music based on mood and duration.
        This implementation generates a simple audio tone or uses local audio files.
        In a production system, you'd connect to a music API or use a licensed music library.
        
        Args:
            mood: The mood of the music
            duration_seconds: Desired duration in seconds
            
        Returns:
            Audio data as bytes
            
        Raises:
            APIError: If getting the background music fails
        """
        try:
            # First, try to find a suitable local audio file
            audio_file = self._find_local_audio(mood)
            if audio_file:
                return self._process_audio_file(audio_file, duration_seconds)
            
            # If no local audio available, generate a simple tone
            return self._generate_tone(mood, duration_seconds)
        except Exception as e:
            logger.error(f"Error getting background music: {str(e)}")
            raise APIError(f"Error getting background music: {str(e)}") from e
    
    def _find_local_audio(self, mood: str) -> Optional[str]:
        """
        Find a suitable local audio file based on mood.
        
        Args:
            mood: The mood of the music
            
        Returns:
            Path to audio file or None if not found
        """
        # This is a placeholder - implement a proper audio file search
        # based on your project's audio assets structure
        audio_dir = os.path.join("data", "assets", "audio")
        
        if not os.path.exists(audio_dir):
            logger.debug(f"Audio directory not found: {audio_dir}")
            return None
        
        # Map moods to keywords
        mood_keywords = {
            "upbeat": ["upbeat", "happy", "energetic", "positive"],
            "calm": ["calm", "peaceful", "relaxing", "ambient"],
            "intense": ["intense", "dramatic", "powerful", "action"],
            "sad": ["sad", "melancholic", "emotional", "slow"],
            "happy": ["happy", "joyful", "cheerful", "bright"]
        }
        
        # Get keywords for the requested mood
        keywords = mood_keywords.get(mood.lower(), [mood.lower()])
        
        # Search for audio files matching the mood
        for root, _, files in os.walk(audio_dir):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                    file_lowercase = file.lower()
                    # Check if any keyword matches the filename
                    if any(keyword in file_lowercase for keyword in keywords):
                        return os.path.join(root, file)
        
        logger.debug(f"No local audio found for mood: {mood}")
        return None
    
    def _process_audio_file(self, file_path: str, duration_seconds: int) -> bytes:
        """
        Process an audio file to match the desired duration.
        
        Args:
            file_path: Path to the audio file
            duration_seconds: Desired duration in seconds
            
        Returns:
            Processed audio data as bytes
        """
        try:
            from pydub import AudioSegment
            
            # Load audio file
            logger.info(f"Processing audio file: {file_path}")
            audio = AudioSegment.from_file(file_path)
            
            # Calculate current duration
            current_duration_ms = len(audio)
            target_duration_ms = duration_seconds * 1000
            
            # If audio is longer than target, trim it
            if current_duration_ms > target_duration_ms:
                audio = audio[:target_duration_ms]
                logger.debug(f"Trimmed audio to {duration_seconds} seconds")
            
            # If audio is shorter than target, loop it
            elif current_duration_ms < target_duration_ms:
                repeats = int(target_duration_ms / current_duration_ms) + 1
                audio = audio * repeats  # Repeat the audio
                audio = audio[:target_duration_ms]  # Trim to exact length
                logger.debug(f"Extended audio to {duration_seconds} seconds by looping")
            
            # Add fade in and fade out
            fade_duration = min(2000, duration_seconds * 500)
            audio = audio.fade_in(fade_duration).fade_out(fade_duration)
            
            # Export to bytes
            output = io.BytesIO()
            audio.export(output, format="mp3")
            output.seek(0)
            
            logger.info("Audio file processed successfully")
            return output.read()
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            raise APIError(f"Error processing audio file: {str(e)}") from e
    
    def _generate_tone(self, mood: str, duration_seconds: int) -> bytes:
        """
        Generate a simple audio tone based on mood.
        
        Args:
            mood: The mood of the tone
            duration_seconds: Duration in seconds
            
        Returns:
            Generated audio data as bytes
        """
        try:
            from pydub import AudioSegment
            from pydub.generators import Sine
            
            logger.info(f"Generating {duration_seconds}s tone with mood: {mood}")
            
            # Map mood to frequency and volume
            mood_settings = {
                "upbeat": {"frequency": 440, "volume": -20},
                "calm": {"frequency": 320, "volume": -25},
                "intense": {"frequency": 520, "volume": -15},
                "sad": {"frequency": 280, "volume": -25},
                "happy": {"frequency": 380, "volume": -20}
            }
            
            settings = mood_settings.get(mood.lower(), mood_settings["upbeat"])
            
            # Generate a simple tone
            sine = Sine(settings["frequency"])
            audio = sine.to_audio_segment(duration=duration_seconds*1000)
            audio = audio.apply_gain(settings["volume"])
            
            # Add fade in and fade out
            fade_duration = min(2000, duration_seconds * 500)
            audio = audio.fade_in(fade_duration).fade_out(fade_duration)
            
            # Export to bytes
            output = io.BytesIO()
            audio.export(output, format="mp3")
            output.seek(0)
            
            logger.info("Tone generated successfully")
            return output.read()
        except Exception as e:
            logger.error(f"Error generating tone: {str(e)}")
            raise APIError(f"Error generating tone: {str(e)}") from e
    
    def mix_audio_tracks(
        self, 
        main_audio: bytes, 
        background_audio: bytes, 
        background_volume: float = -10
    ) -> bytes:
        """
        Mix main audio track with background audio track.
        
        Args:
            main_audio: Main audio data (e.g., voiceover)
            background_audio: Background audio data (e.g., music)
            background_volume: Volume adjustment for background in dB
            
        Returns:
            Mixed audio data as bytes
            
        Raises:
            APIError: If mixing fails
        """
        try:
            from pydub import AudioSegment
            
            logger.info("Mixing audio tracks")
            
            # Load audio data
            main_io = io.BytesIO(main_audio)
            bg_io = io.BytesIO(background_audio)
            
            main_track = AudioSegment.from_file(main_io)
            bg_track = AudioSegment.from_file(bg_io)
            
            # Adjust background volume
            bg_track = bg_track.apply_gain(background_volume)
            
            # Ensure background is same length as main track
            if len(bg_track) < len(main_track):
                # Loop background if needed
                repeats = int(len(main_track) / len(bg_track)) + 1
                bg_track = bg_track * repeats
            
            # Trim background to match main track
            bg_track = bg_track[:len(main_track)]
            
            # Mix tracks
            mixed = main_track.overlay(bg_track)
            
            # Export to bytes
            output = io.BytesIO()
            mixed.export(output, format="mp3")
            output.seek(0)
            
            logger.info("Audio tracks mixed successfully")
            return output.read()
        except Exception as e:
            logger.error(f"Error mixing audio tracks: {str(e)}")
            raise APIError(f"Error mixing audio tracks: {str(e)}") from e
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            params: URL parameters
            data: Request body data
            json_data: JSON data for the request body
            headers: HTTP headers
            
        Returns:
            Response object
            
        Raises:
            APIError: If the request fails
        """
        # Set up default headers
        if headers is None:
            headers = {}
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            return response
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise APIError(f"API request failed: {str(e)}") from e