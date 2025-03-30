"""
Video generator for YouTube Shorts Automation System.
Assembles images into video sequences with transitions and effects.
"""
import logging
import os
import tempfile
import random
from typing import List, Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np
import moviepy as mpy
from moviepy import ImageSequenceClip, ImageClip, CompositeVideoClip, TextClip, ColorClip
from PIL import Image

from utils.error_handling import MediaError, retry, safe_execute
from utils.file_management import FileManager
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class VideoGenerator:
    """
    Assembles images into video sequences with transitions and effects.
    """
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        file_manager: FileManager
    ):
        """
        Initialize the video generator.
        
        Args:
            config_loader: Configuration loader instance
            file_manager: File manager instance
        """
        self.config = config_loader
        self.file_manager = file_manager
        
        # Load configuration values
        self.resolution = self._parse_resolution(
            self.config.get_config_value("video.resolution", "1080x1920")
        )
        self.fps = self.config.get_config_value("video.fps", 30)
        self.duration_seconds = self.config.get_config_value("video.duration_seconds", 60)
        
        # Configure FFmpeg paths
        self._configure_ffmpeg()
        
        logger.info("Video generator initialized")
    
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
            logger.info(f"FFmpeg configured with binary at {ffmpeg_binary}")
        else:
            logger.warning("FFmpeg binaries not found at expected locations. Using system defaults.")
    
    def _parse_resolution(self, resolution_str: str) -> Tuple[int, int]:
        """
        Parse resolution string into width and height.
        
        Args:
            resolution_str: Resolution string in format 'WIDTHxHEIGHT'
            
        Returns:
            Tuple of (width, height)
        """
        try:
            width, height = resolution_str.lower().split('x')
            return (int(width), int(height))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid resolution format: {resolution_str}. Using default 1080x1920.")
            return (1080, 1920)
    
    def create_video_from_images(
        self,
        image_paths: List[str],
        output_path: str,
        captions: Optional[List[str]] = None,
        total_duration: Optional[float] = None,
        transition_duration: float = 1.0,
        add_intro: bool = False,
        add_outro: bool = False,
        title: Optional[str] = None
    ) -> str:
        """
        Create a video from a sequence of images.
        
        Args:
            image_paths: List of paths to the images
            output_path: Path to save the video
            captions: Optional list of captions for each image
            total_duration: Optional total duration of the video in seconds
            transition_duration: Duration of transitions between images in seconds
            add_intro: Whether to add an intro clip
            add_outro: Whether to add an outro clip
            title: Optional title for the video
            
        Returns:
            Path to the created video
            
        Raises:
            MediaError: If video creation fails
        """
        if not image_paths:
            raise MediaError("No images provided for video creation")
        
        # Set default values
        if total_duration is None:
            total_duration = self.duration_seconds
        
        # Calculate duration per image
        num_images = len(image_paths)
        # Subtract transitions (one less than images) from total duration
        effective_duration = total_duration - transition_duration * (num_images - 1)
        # Subtract intro and outro durations if used
        intro_duration = 2.0 if add_intro else 0
        outro_duration = 3.0 if add_outro else 0
        effective_duration -= (intro_duration + outro_duration)
        
        if effective_duration <= 0:
            logger.warning("Not enough duration for all content. Adjusting parameters.")
            transition_duration = 0.5
            effective_duration = total_duration - transition_duration * (num_images - 1) - (intro_duration + outro_duration)
            if effective_duration <= 0:
                # If still not enough time, disable intro/outro
                intro_duration = outro_duration = 0
                add_intro = add_outro = False
                effective_duration = total_duration - transition_duration * (num_images - 1)
        
        # Duration per image should be at least 1 second
        duration_per_image = max(1.0, effective_duration / num_images)
        
        logger.info(f"Creating video with {num_images} images, {duration_per_image:.2f}s per image")
        
        try:
            # Create individual clips for each image
            clips = []
            
            # Add intro if requested
            if add_intro:
                intro_clip = self._create_intro_clip(title, intro_duration)
                clips.append(intro_clip)
            
            # Process each image
            for i, img_path in enumerate(image_paths):
                # Create image clip
                image_clip = ImageClip(img_path, duration=duration_per_image)
                
                # Ensure clip has the correct size
                width, height = self.resolution
                if image_clip.size != (width, height):
                    image_clip = image_clip.resize(width=width, height=height)
                
                # Add text caption if provided
                if captions and i < len(captions) and captions[i]:
                    caption = captions[i]
                    txt_clip = TextClip(caption, fontsize=40, color='white', stroke_color='black',
                                      stroke_width=1, size=(width * 0.8, None), method='caption')
                    txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(duration_per_image)
                    
                    # Add background to text for better visibility
                    txt_bg = ColorClip(size=(width, txt_clip.size[1] + 20),
                                      color=(0, 0, 0), duration=duration_per_image)
                    txt_bg = txt_bg.set_opacity(0.6).set_position(('center', 'bottom'))
                    
                    # Composite the image, text background, and text
                    image_clip = CompositeVideoClip([image_clip, txt_bg, txt_clip])
                
                # Add transitions (fade in/out) except for first/last clips
                if i > 0:
                    image_clip = image_clip.fadein(transition_duration/2)
                if i < num_images - 1:
                    image_clip = image_clip.fadeout(transition_duration/2)
                
                # Set start time
                if i == 0:
                    start_time = intro_duration
                else:
                    # Each clip starts after previous clip minus half the transition overlap
                    start_time = intro_duration + i * duration_per_image - i * transition_duration/2
                
                image_clip = image_clip.set_start(start_time)
                clips.append(image_clip)
            
            # Add outro if requested
            if add_outro:
                outro_start = intro_duration + num_images * duration_per_image - (num_images - 1) * transition_duration/2
                outro_clip = self._create_outro_clip(title, outro_duration).set_start(outro_start)
                clips.append(outro_clip)
            
            # Create the final video with all clips
            final_clip = CompositeVideoClip(clips, size=self.resolution)
            final_duration = intro_duration + num_images * duration_per_image - (num_images - 1) * transition_duration/2 + outro_duration
            final_clip = final_clip.set_duration(final_duration)
            
            # Set the FPS
            final_clip = final_clip.set_fps(self.fps)
            
            # Write the final video to file
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio=False,
                preset='medium',
                bitrate='8000k',
                threads=4,
                logger=None  # Disable moviepy's internal logger
            )
            
            logger.info(f"Video created successfully: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            raise MediaError(f"Failed to create video: {str(e)}") from e
        finally:
            # Clean up resources
            try:
                for clip in clips:
                    clip.close() if 'clips' in locals() else None
                final_clip.close() if 'final_clip' in locals() else None
            except Exception as e:
                logger.warning(f"Error cleaning up resources: {e}")
    
    def _create_intro_clip(self, title: Optional[str], duration: float) -> CompositeVideoClip:
        """
        Create an intro clip for the video.
        
        Args:
            title: Title to display in the intro
            duration: Duration of the intro in seconds
            
        Returns:
            Intro clip
        """
        width, height = self.resolution
        
        # Create background
        bg_clip = ColorClip(size=self.resolution, color=(0, 0, 0), duration=duration)
        
        # Create elements for intro
        clips = [bg_clip]
        
        if title:
            # Add title text
            title_clip = TextClip(title, fontsize=60, color='white', size=(width * 0.8, None),
                                method='caption', align='center')
            title_clip = title_clip.set_position('center').set_duration(duration)
            
            # Add fade in animation
            title_clip = title_clip.fadein(duration/2)
            
            clips.append(title_clip)
        
        # Create branding text
        brand_text = self.config.get_config_value("content.brand_text", "Generated Video")
        brand_clip = TextClip(brand_text, fontsize=30, color='gray', size=(width * 0.8, None))
        brand_clip = brand_clip.set_position(('center', 'bottom')).set_duration(duration)
        brand_clip = brand_clip.fadein(duration/2)
        
        clips.append(brand_clip)
        
        # Composite all elements
        intro_clip = CompositeVideoClip(clips, size=self.resolution)
        
        return intro_clip
    
    def _create_outro_clip(self, title: Optional[str], duration: float) -> CompositeVideoClip:
        """
        Create an outro clip for the video.
        
        Args:
            title: Title to reference in the outro
            duration: Duration of the outro in seconds
            
        Returns:
            Outro clip
        """
        width, height = self.resolution
        
        # Create background
        bg_clip = ColorClip(size=self.resolution, color=(0, 0, 0), duration=duration)
        
        # Create elements for outro
        clips = [bg_clip]
        
        # Create thank you text
        thank_you_text = "Thanks for watching!"
        thanks_clip = TextClip(thank_you_text, fontsize=60, color='white', size=(width * 0.8, None))
        thanks_clip = thanks_clip.set_position(('center', 'top')).set_duration(duration)
        thanks_clip = thanks_clip.set_start(0.5).fadein(0.5)
        
        clips.append(thanks_clip)
        
        # Add subscribe call to action
        subscribe_text = "Subscribe for more!"
        subscribe_clip = TextClip(subscribe_text, fontsize=50, color='white', size=(width * 0.8, None))
        subscribe_clip = subscribe_clip.set_position('center').set_duration(duration - 0.5)
        subscribe_clip = subscribe_clip.set_start(1.0).fadein(0.5)
        
        clips.append(subscribe_clip)
        
        # Add branding or channel name if available
        brand_text = self.config.get_config_value("content.brand_text", "Generated Video")
        brand_clip = TextClip(brand_text, fontsize=40, color='gray', size=(width * 0.8, None))
        brand_clip = brand_clip.set_position(('center', 'bottom')).set_duration(duration - 1.0)
        brand_clip = brand_clip.set_start(1.5).fadein(0.5)
        
        clips.append(brand_clip)
        
        # Composite all elements
        outro_clip = CompositeVideoClip(clips, size=self.resolution)
        
        return outro_clip
    
    def add_transitions(
        self, 
        input_path: str, 
        output_path: str, 
        transition_type: str = 'fade'
    ) -> str:
        """
        Add transitions between scenes in the video.
        
        Args:
            input_path: Path to the input video
            output_path: Path to save the output video
            transition_type: Type of transition to add
            
        Returns:
            Path to the processed video
            
        Raises:
            MediaError: If adding transitions fails
        """
        try:
            # Load the video clip
            video = mpy.VideoFileClip(input_path)
            
            # Create a copy of the clip with the transition
            if transition_type == 'fade':
                # Add fade in at the beginning and fade out at the end
                video = video.fadein(1.0).fadeout(1.0)
            
            # Write the result
            video.write_videofile(
                output_path,
                codec='libx264',
                audio=False if not video.audio else True,
                preset='medium',
                bitrate='8000k',
                threads=4,
                logger=None  # Disable moviepy's internal logger
            )
            
            logger.info(f"Added {transition_type} transitions to video: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding transitions: {str(e)}")
            raise MediaError(f"Failed to add transitions: {str(e)}") from e
        finally:
            try:
                video.close() if 'video' in locals() else None
            except Exception as e:
                logger.warning(f"Error cleaning up resources: {e}")
    
    def add_effects(
        self, 
        input_path: str, 
        output_path: str, 
        effects: List[str] = ['zoom']
    ) -> str:
        """
        Add visual effects to the video.
        
        Args:
            input_path: Path to the input video
            output_path: Path to save the output video
            effects: List of effects to apply
            
        Returns:
            Path to the processed video
            
        Raises:
            MediaError: If adding effects fails
        """
        try:
            # Load the video clip
            video = mpy.VideoFileClip(input_path)
            
            # Apply the specified effects
            for effect in effects:
                if effect == 'zoom':
                    # Apply subtle zoom effect
                    def zoom_effect(t):
                        # Start with no zoom, end with 10% zoom
                        zoom_factor = 1.0 + 0.1 * t / video.duration
                        return zoom_factor
                    
                    video = video.resize(zoom_effect)
                
                elif effect == 'blur_background':
                    # This is a more complex effect that would require frame-by-frame processing
                    # Simplified version here just for demonstration
                    pass
                
                # Add more effects as needed
            
            # Write the result
            video.write_videofile(
                output_path,
                codec='libx264',
                audio=False if not video.audio else True,
                preset='medium',
                bitrate='8000k',
                threads=4,
                logger=None  # Disable moviepy's internal logger
            )
            
            logger.info(f"Added effects {effects} to video: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding effects: {str(e)}")
            raise MediaError(f"Failed to add effects: {str(e)}") from e
        finally:
            try:
                video.close() if 'video' in locals() else None
            except Exception as e:
                logger.warning(f"Error cleaning up resources: {e}")
    
    def create_video_with_ken_burns(
        self,
        image_paths: List[str],
        output_path: str,
        captions: Optional[List[str]] = None,
        total_duration: Optional[float] = None
    ) -> str:
        """
        Create a video with Ken Burns effect (pan and zoom) on still images.
        
        Args:
            image_paths: List of paths to the images
            output_path: Path to save the video
            captions: Optional list of captions for each image
            total_duration: Optional total duration of the video in seconds
            
        Returns:
            Path to the created video
            
        Raises:
            MediaError: If video creation fails
        """
        if not image_paths:
            raise MediaError("No images provided for video creation")
        
        # Set default values
        if total_duration is None:
            total_duration = self.duration_seconds
        
        # Calculate duration per image
        num_images = len(image_paths)
        duration_per_image = total_duration / num_images
        
        logger.info(f"Creating Ken Burns effect video with {num_images} images")
        
        try:
            clips = []
            
            for i, img_path in enumerate(image_paths):
                # Load the image
                orig_img = ImageClip(img_path)
                
                # Define the Ken Burns effect
                # The effect randomly zooms in or out and pans across the image
                zoom_in = random.choice([True, False])
                
                def ken_burns_effect(t):
                    progress = t / duration_per_image
                    
                    if zoom_in:
                        # Zoom in effect (1.0 to 1.2)
                        zoom = 1.0 + 0.2 * progress
                        pos_x = 0.1 * progress * orig_img.w
                        pos_y = 0.1 * progress * orig_img.h
                    else:
                        # Zoom out effect (1.2 to 1.0)
                        zoom = 1.2 - 0.2 * progress
                        pos_x = 0.1 * (1 - progress) * orig_img.w
                        pos_y = 0.1 * (1 - progress) * orig_img.h
                    
                    return (zoom, pos_x, pos_y)
                
                # Apply the Ken Burns effect
                w, h = self.resolution
                
                def effect_func(get_frame, t):
                    frame = get_frame(t)
                    zoom, pos_x, pos_y = ken_burns_effect(t)
                    
                    # Resize the frame with zoom
                    zoomed_h = int(h * zoom)
                    zoomed_w = int(w * zoom)
                    
                    frame = cv2.resize(frame, (zoomed_w, zoomed_h))
                    
                    # Crop to the final size
                    x1 = int(min(pos_x, frame.shape[1] - w))
                    y1 = int(min(pos_y, frame.shape[0] - h))
                    x2 = int(x1 + w)
                    y2 = int(y1 + h)
                    
                    # Ensure boundaries are valid
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(frame.shape[1], x2)
                    y2 = min(frame.shape[0], y2)
                    
                    return frame[y1:y2, x1:x2]
                
                # Create the clip with the effect
                img_clip = mpy.VideoClip(lambda t: effect_func(orig_img.get_frame, t),
                                         duration=duration_per_image)
                
                # Add caption if provided
                if captions and i < len(captions) and captions[i]:
                    caption = captions[i]
                    txt_clip = TextClip(caption, fontsize=40, color='white', stroke_color='black',
                                      stroke_width=1, size=(w * 0.8, None), method='caption')
                    txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(duration_per_image)
                    
                    # Add a semi-transparent background for the text
                    txt_bg = ColorClip(size=(w, txt_clip.size[1] + 20),
                                      color=(0, 0, 0), duration=duration_per_image)
                    txt_bg = txt_bg.set_opacity(0.6).set_position(('center', 'bottom'))
                    
                    img_clip = CompositeVideoClip([img_clip, txt_bg, txt_clip])
                
                # Add fade transitions
                if i > 0:
                    img_clip = img_clip.fadein(0.5)
                if i < num_images - 1:
                    img_clip = img_clip.fadeout(0.5)
                
                clips.append(img_clip)
            
            # Concatenate all clips
            final_clip = mpy.concatenate_videoclips(clips)
            
            # Set the FPS
            final_clip = final_clip.set_fps(self.fps)
            
            # Write the final video to file
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio=False,
                preset='medium',
                bitrate='8000k',
                threads=4,
                logger=None  # Disable moviepy's internal logger
            )
            
            logger.info(f"Ken Burns effect video created successfully: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating Ken Burns effect video: {str(e)}")
            raise MediaError(f"Failed to create Ken Burns effect video: {str(e)}") from e
        finally:
            try:
                for clip in clips:
                    clip.close() if 'clips' in locals() else None
                final_clip.close() if 'final_clip' in locals() else None
            except Exception as e:
                logger.warning(f"Error cleaning up resources: {e}")