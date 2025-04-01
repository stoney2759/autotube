"""
Video Rendering Module for YouTube Shorts Automation.
Combines video and audio tracks with final processing.
"""
import logging
import os
import yaml
from datetime import datetime
import json
import time
import subprocess
import numpy as np

# Import directly from moviepy
try:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, 
        concatenate_videoclips
    )
except ImportError:
    # Fallback imports for older versions
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, 
        concatenate_videoclips
    )


class VideoRenderer:
    """
    Renders final videos by combining video tracks, audio,
    titles, captions and other elements.
    """
    
    def __init__(self, config_loader=None, file_manager=None):
        """
        Initialize video renderer with configuration
        
        Args:
            config_loader: Configuration loader instance
            file_manager: File manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Video Renderer")
        
        self.file_manager = file_manager
        self.config = None
        
        # Load configuration
        if config_loader:
            self.config = {}
            # Get config values from the loader
            video_config = {
                'resolution': config_loader.get_config_value("video.resolution", "1080x1920"),
                'duration_seconds': config_loader.get_config_value("video.duration_seconds", 60),
                'fps': config_loader.get_config_value("video.fps", 30)
            }
            renderer_config = {
                'watermark': config_loader.get_config_value("renderer.watermark", False),
                'add_title': config_loader.get_config_value("renderer.add_title", True),
                'title_duration': config_loader.get_config_value("renderer.title_duration", 3),
                'end_card_duration': config_loader.get_config_value("renderer.end_card_duration", 2)
            }
            
            self.config['video'] = video_config
            self.config['renderer'] = renderer_config
            self.logger.debug("Loaded configuration from config loader")
        else:
            # Load from file as fallback
            try:
                config_path = 'config/config.yaml'
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
        try:
            import moviepy
            
            ffmpeg_binary = os.environ.get('FFMPEG_BINARY', 'C:\\ffmpeg\\bin\\ffmpeg.exe')
            ffprobe_binary = os.environ.get('FFPROBE_BINARY', 'C:\\ffmpeg\\bin\\ffprobe.exe')
            
            if os.path.exists(ffmpeg_binary) and os.path.exists(ffprobe_binary):
                # Set the environment variables that MoviePy will use
                os.environ['FFMPEG_BINARY'] = ffmpeg_binary
                os.environ['FFPROBE_BINARY'] = ffprobe_binary
                
                # Update moviepy's config manually if possible
                try:
                    moviepy.config.FFMPEG_BINARY = ffmpeg_binary
                    moviepy.config.FFPROBE_BINARY = ffprobe_binary
                except:
                    pass
                    
                self.logger.info(f"FFmpeg configured with binary at {ffmpeg_binary}")
            else:
                self.logger.warning("FFmpeg binaries not found at expected locations. Using system defaults.")
        except Exception as e:
            self.logger.error(f"Error configuring FFmpeg: {e}")
    
    def render_final_video(
        self,
        project_id,
        video_path,
        audio_path,
        title=None,
        captions=None,
        add_watermark=True
    ):
        """
        Render the final video by combining video and audio.
        
        Args:
            project_id: Project ID for organization
            video_path: Path to the base video
            audio_path: Path to the audio file
            title: Optional title for the video
            captions: Optional captions for the video
            add_watermark: Whether to add a watermark
            
        Returns:
            Path to the rendered video
        """
        # Create output path
        if self.file_manager:
            output_dir = os.path.join(self.file_manager.assets_dir, project_id, "video")
        else:
            output_dir = os.path.join('data', 'assets', project_id, 'video')
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = int(time.time())
        output_filename = f"final_video_{timestamp}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        # Create simple metadata object
        metadata = {}
        if title:
            metadata["title"] = title
        
        # First, try using direct FFmpeg for combining video and audio
        success = self._combine_with_ffmpeg(video_path, audio_path, output_path)
        if success:
            # Save metadata
            metadata_path = output_path + ".json"
            self._save_metadata(metadata_path, metadata)
            self.logger.info(f"Video rendered successfully: {output_path}")
            return output_path
            
        # If FFmpeg direct combination fails, fall back to the regular render method
        return self.render_video(video_path, audio_path, metadata, output_path)
    
    def _combine_with_ffmpeg(self, video_path, audio_path, output_path):
        """Use FFmpeg directly to combine video and audio files"""
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return False
            
        if not os.path.exists(audio_path):
            self.logger.error(f"Audio file not found: {audio_path}")
            return False
            
        try:
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # Copy video stream without re-encoding
                '-c:a', 'aac',   # Use AAC for audio
                '-shortest',     # End when the shortest input stream ends
                output_path
            ]
            
            self.logger.info(f"Combining video and audio with FFmpeg: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=120)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.logger.info(f"Successfully combined video and audio using FFmpeg")
                return True
            else:
                self.logger.warning("FFmpeg completed but output file is missing or empty")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error using FFmpeg to combine: {str(e)}")
            return False
    
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
            
            # First try direct FFmpeg approach for audio
            if audio_path and os.path.exists(audio_path):
                # Create temporary output video with no audio
                temp_video_path = output_path.replace('.mp4', '_temp.mp4')
                video.without_audio().write_videofile(
                    temp_video_path,
                    fps=fps,
                    codec='libx264',
                    preset='medium',
                    bitrate='8000k',
                    threads=2,
                    logger=None
                )
                
                # Now combine the silent video with audio using FFmpeg
                success = self._combine_with_ffmpeg(temp_video_path, audio_path, output_path)
                
                # If direct FFmpeg approach worked, clean up and return
                if success and os.path.exists(output_path):
                    if os.path.exists(temp_video_path):
                        try:
                            os.remove(temp_video_path)
                        except:
                            pass
                    
                    # Save metadata
                    metadata_path = output_path + ".json"
                    self._save_metadata(metadata_path, metadata)
                    
                    self.logger.info(f"Video rendered with FFmpeg: {output_path}")
                    return output_path
            
            # Fallback: Try using MoviePy for both video and audio
            if audio_path and os.path.exists(audio_path):
                try:
                    self.logger.info(f"Adding audio from {audio_path}")
                    audio = AudioFileClip(audio_path)
                    
                    # Adjust audio duration to match video
                    if audio.duration > video.duration:
                        audio = audio.subclip(0, video.duration)
                    elif audio.duration < video.duration:
                        # Loop audio if needed
                        repeat_factor = int(video.duration / audio.duration) + 1
                        audio_list = [audio] * repeat_factor
                        audio = concatenate_videoclips(audio_list).subclip(0, video.duration)
                    
                    # Set audio to video
                    video = video.set_audio(audio)
                except Exception as e:
                    self.logger.error(f"Error adding audio with MoviePy: {e}")
            
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
                preset='medium',
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
            
            # Try one last approach using FFmpeg directly
            if os.path.exists(video_path) and audio_path and os.path.exists(audio_path):
                success = self._combine_with_ffmpeg(video_path, audio_path, output_path)
                if success:
                    self.logger.info(f"Video created with FFmpeg fallback: {output_path}")
                    return output_path
            
            return None
        finally:
            # Clean up resources
            try:
                if 'video' in locals() and video is not None:
                    video.close()
                if 'audio' in locals() and audio is not None:
                    audio.close()
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
            
    def compress_video(self, video_path, output_path, target_size_mb=100):
        """
        Compress a video to target file size
        
        Args:
            video_path (str): Path to the video to compress
            output_path (str): Path to save the compressed video
            target_size_mb (int): Target size in megabytes
            
        Returns:
            str: Path to the compressed video
        """
        try:
            # Try using FFmpeg directly
            # Calculate target bitrate based on file size and duration
            duration_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            duration_result = subprocess.run(
                duration_cmd, 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            if duration_result.returncode == 0:
                try:
                    duration = float(duration_result.stdout.strip())
                except (ValueError, TypeError):
                    # Fallback duration if parsing fails
                    duration = 60.0
            else:
                # Fallback duration
                duration = 60.0
            
            # Calculate target bitrate (bits per second)
            # Formula: target_size_in_bits / duration_in_seconds
            target_size_bits = target_size_mb * 8 * 1024 * 1024
            target_bitrate = int(target_size_bits / duration)
            
            # Convert to kbps string format
            target_bitrate_kbps = str(target_bitrate // 1000)
            
            self.logger.info(f"Compressing video to target bitrate: {target_bitrate_kbps} kbps")
            
            # Use two-pass encoding for better quality
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-c:v', 'libx264', '-b:v', f'{target_bitrate_kbps}k',
                '-c:a', 'aac', '-b:a', '128k',
                '-pass', '1', '-f', 'null', 'NUL'
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, timeout=300)
            
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-c:v', 'libx264', '-b:v', f'{target_bitrate_kbps}k',
                '-c:a', 'aac', '-b:a', '128k',
                '-pass', '2', output_path
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, timeout=300)
            
            self.logger.info(f"Video compressed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error compressing video: {e}")
            
            # Try fallback method using MoviePy
            try:
                video = VideoFileClip(video_path)
                video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    bitrate=f"{target_size_mb // 10}M",  # Rough estimate
                    preset='medium',
                    threads=2,
                    logger=None
                )
                video.close()
                return output_path
            except Exception as e2:
                self.logger.error(f"Error in fallback compression: {e2}")
                return video_path  # Return original if compression fails