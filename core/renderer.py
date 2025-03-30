"""
Video Rendering Module for YouTube Shorts Automation.
Combines video and audio tracks with final processing.
"""
import logging
import os
import yaml
from datetime import datetime
import json

# Import directly from moviepy (for version 2.1.2+)
from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, 
    concatenate_videoclips, vfx
)

class VideoRenderer:
    """
    Renders final videos by combining video tracks, audio,
    titles, captions and other elements.
    """
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialize video renderer with configuration
        
        Args:
            config_path (str): Path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Video Renderer")
        
        # Load configuration
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            self.logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {
                'video': {
                    'resolution': '1080x1920',  # Vertical for shorts
                    'duration_seconds': 60,
                    'fps': 30
                },
                'renderer': {
                    'watermark': False,
                    'add_title': True,
                    'title_duration': 3,
                    'end_card_duration': 2
                }
            }
            self.logger.warning("Using default renderer configuration")
        
        # Create output directory
        self.output_dir = os.path.join('data', 'assets', 'video', 'rendered')
        os.makedirs(self.output_dir, exist_ok=True)
        
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
    
    def render_video(self, video_path, audio_path=None, metadata=None, output_path=None):
        """
        Render a final video with all elements combined
        
        Args:
            video_path (str): Path to the base video
            audio_path (str, optional): Path to the audio file
            metadata (dict, optional): Video metadata
            output_path (str, optional): Path to save the rendered video
            
        Returns:
            str: Path to the rendered video
        """
        if not video_path or not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return None
        
        if metadata is None:
            metadata = {}
        
        # Create output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"rendered_{timestamp}.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
        
        # Get configuration
        renderer_config = self.config.get('renderer', {})
        video_config = self.config.get('video', {})
        fps = video_config.get('fps', 30)
        
        try:
            # Load the video
            self.logger.info(f"Loading video from {video_path}")
            video = VideoFileClip(video_path)
            
            # If audio is provided, add it to the video
            if audio_path and os.path.exists(audio_path) and not video.audio:
                self.logger.info(f"Adding audio from {audio_path}")
                try:
                    audio = AudioFileClip(audio_path)
                    
                    # Adjust audio duration to match video
                    if audio.duration > video.duration:
                        audio = audio.subclip(0, video.duration)
                    elif audio.duration < video.duration:
                        # Loop audio if needed
                        n_loops = int(video.duration / audio.duration) + 1
                        audio = concatenate_videoclips([audio] * n_loops).subclip(0, video.duration)
                    
                    # Set audio to video
                    video = video.set_audio(audio)
                except Exception as e:
                    self.logger.error(f"Error adding audio: {e}")
            
            # Add title/intro if configured
            video = self._add_title_screen(video, metadata)
            
            # Add captions if available
            video = self._add_captions(video, metadata)
            
            # Add watermark if configured
            if renderer_config.get('watermark', False):
                video = self._add_watermark(video, metadata)
            
            # Add end card if configured
            video = self._add_end_card(video, metadata)
            
            # Final processing (color grading, etc.)
            video = self._apply_final_processing(video)
            
            # Write the final video
            self.logger.info(f"Writing rendered video to {output_path}")
            video.write_videofile(
                output_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                preset='medium',  # Quality/speed tradeoff ('ultrafast' to 'veryslow')
                bitrate='8000k',
                threads=2,
                logger=None  # Use internal logger
            )
            
            # Save metadata
            metadata_path = output_path + ".json"
            self._save_metadata(metadata_path, metadata)
            
            self.logger.info(f"Video rendered successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error rendering video: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
        finally:
            # Clean up resources
            try:
                video.close() if 'video' in locals() else None
                audio.close() if 'audio' in locals() else None
            except Exception as e:
                self.logger.warning(f"Error cleaning up resources: {e}")
    
    def _add_title_screen(self, video, metadata):
        """
        Add a title screen to the beginning of the video
        
        Args:
            video: MoviePy video clip
            metadata (dict): Video metadata
            
        Returns:
            MoviePy clip: Video with title screen
        """
        renderer_config = self.config.get('renderer', {})
        if not renderer_config.get('add_title', True) or not metadata.get('title'):
            return video
        
        try:
            title_text = metadata.get('title', '')
            title_duration = renderer_config.get('title_duration', 3)
            
            # Parse resolution
            video_config = self.config.get('video', {})
            resolution_str = video_config.get('resolution', '1080x1920')
            width, height = map(int, resolution_str.split('x'))
            
            # This is a placeholder for actual title screen creation
            # In a full implementation, this would create a TextClip and combine it with the video
            # For now, we'll just return the original video
            self.logger.info(f"Title screen would be added here: {title_text}")
            
            return video
            
        except Exception as e:
            self.logger.error(f"Error adding title screen: {e}")
            return video
    
    def _add_captions(self, video, metadata):
        """
        Add captions to the video
        
        Args:
            video: MoviePy video clip
            metadata (dict): Video metadata
            
        Returns:
            MoviePy clip: Video with captions
        """
        # This is a placeholder for caption addition
        # In a full implementation, this would add text overlays at specific times
        return video
    
    def _add_watermark(self, video, metadata):
        """
        Add a watermark to the video
        
        Args:
            video: MoviePy video clip
            metadata (dict): Video metadata
            
        Returns:
            MoviePy clip: Video with watermark
        """
        renderer_config = self.config.get('renderer', {})
        if not renderer_config.get('watermark', False):
            return video
        
        try:
            # This is a placeholder for watermark addition
            # In a full implementation, this would add a semi-transparent logo
            self.logger.info("Watermark would be added here")
            
            return video
            
        except Exception as e:
            self.logger.error(f"Error adding watermark: {e}")
            return video
    
    def _add_end_card(self, video, metadata):
        """
        Add an end card to the video
        
        Args:
            video: MoviePy video clip
            metadata (dict): Video metadata
            
        Returns:
            MoviePy clip: Video with end card
        """
        renderer_config = self.config.get('renderer', {})
        if not renderer_config.get('add_end_card', False):
            return video
        
        try:
            # This is a placeholder for end card addition
            # In a full implementation, this would add a call-to-action screen at the end
            self.logger.info("End card would be added here")
            
            return video
            
        except Exception as e:
            self.logger.error(f"Error adding end card: {e}")
            return video
    
    def _apply_final_processing(self, video):
        """
        Apply final processing to the video (color grading, etc.)
        
        Args:
            video: MoviePy video clip
            
        Returns:
            MoviePy clip: Processed video
        """
        try:
            # This is a placeholder for final processing
            # In a full implementation, this would apply color grading, etc.
            self.logger.info("Final processing would be applied here")
            
            return video
            
        except Exception as e:
            self.logger.error(f"Error applying final processing: {e}")
            return video
    
    def _save_metadata(self, metadata_path, metadata):
        """
        Save video metadata to a JSON file
        
        Args:
            metadata_path (str): Path to save metadata
            metadata (dict): Video metadata
        """
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            self.logger.info(f"Metadata saved to {metadata_path}")
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")