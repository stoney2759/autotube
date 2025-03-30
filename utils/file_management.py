"""
File management utilities for YouTube Shorts Automation System.
Handles file operations, asset management, and directory structure.
"""
import os
import logging
import shutil
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class FileManager:
    """
    Handles file operations for the automation system including
    creating directories, managing assets, and tracking generated content.
    """
    
    def __init__(self, 
                 base_dir: str = "data",
                 content_db_dir: str = "content_db",
                 output_tracking_dir: str = "output_tracking",
                 assets_dir: str = "assets",
                 image_dir: str = "images",
                 audio_dir: str = "audio",
                 video_dir: str = "video"):
        """
        Initialize the file manager.
        
        Args:
            base_dir: Base directory for all data
            content_db_dir: Directory for content database
            output_tracking_dir: Directory for output tracking
            assets_dir: Directory for media assets
            image_dir: Directory for images (under assets)
            audio_dir: Directory for audio files (under assets)
            video_dir: Directory for video files (under assets)
        """
        # Set directory paths
        self.base_dir = Path(base_dir)
        self.content_db_dir = self.base_dir / content_db_dir
        self.output_tracking_dir = self.base_dir / output_tracking_dir
        self.assets_dir = self.base_dir / assets_dir
        self.image_dir = self.assets_dir / image_dir
        self.audio_dir = self.assets_dir / audio_dir
        self.video_dir = self.assets_dir / video_dir
        
        # Create directory structure
        self._create_directory_structure()
        
        logger.info("File manager initialized")
    
    def _create_directory_structure(self) -> None:
        """Create the necessary directory structure for the application."""
        directories = [
            self.base_dir,
            self.content_db_dir,
            self.output_tracking_dir,
            self.assets_dir,
            self.image_dir,
            self.audio_dir,
            self.video_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def create_project_dir(self, project_name: str = None) -> Tuple[str, str]:
        """
        Create a new project directory with unique ID for a video generation run.
        
        Args:
            project_name: Optional project name prefix
            
        Returns:
            Tuple of (project_id, project_directory_path)
        """
        # Generate a unique project ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if project_name:
            # Clean project name (remove special characters and spaces)
            clean_name = ''.join(c if c.isalnum() else '_' for c in project_name)
            project_id = f"{clean_name}_{timestamp}_{unique_id}"
        else:
            project_id = f"project_{timestamp}_{unique_id}"
        
        # Create project directories
        project_dir = self.assets_dir / project_id
        project_image_dir = project_dir / "images"
        project_audio_dir = project_dir / "audio"
        project_video_dir = project_dir / "video"
        
        project_dir.mkdir(parents=True, exist_ok=True)
        project_image_dir.mkdir(exist_ok=True)
        project_audio_dir.mkdir(exist_ok=True)
        project_video_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created project directory: {project_dir}")
        
        return project_id, str(project_dir)
    
    def save_image(self, image_data: bytes, project_id: str, filename: str = None) -> str:
        """
        Save an image to the project's image directory.
        
        Args:
            image_data: Binary image data
            project_id: The project ID
            filename: Optional filename (if None, a unique name will be generated)
            
        Returns:
            The path to the saved image
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"image_{timestamp}_{uuid.uuid4().hex[:6]}.png"
        
        # Ensure the extension is included
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'
        
        project_image_dir = self.assets_dir / project_id / "images"
        image_path = project_image_dir / filename
        
        try:
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            logger.debug(f"Saved image to {image_path}")
            return str(image_path)
        except Exception as e:
            logger.error(f"Error saving image {filename}: {str(e)}")
            raise
    
    def save_audio(self, audio_data: bytes, project_id: str, filename: str = None) -> str:
        """
        Save an audio file to the project's audio directory.
        
        Args:
            audio_data: Binary audio data
            project_id: The project ID
            filename: Optional filename (if None, a unique name will be generated)
            
        Returns:
            The path to the saved audio file
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"audio_{timestamp}_{uuid.uuid4().hex[:6]}.mp3"
        
        # Ensure the extension is included
        if not filename.lower().endswith(('.mp3', '.wav', '.ogg')):
            filename += '.mp3'
        
        project_audio_dir = self.assets_dir / project_id / "audio"
        audio_path = project_audio_dir / filename
        
        try:
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            logger.debug(f"Saved audio to {audio_path}")
            return str(audio_path)
        except Exception as e:
            logger.error(f"Error saving audio {filename}: {str(e)}")
            raise
    
    def save_video(self, video_data: bytes, project_id: str, filename: str = None) -> str:
        """
        Save a video file to the project's video directory.
        
        Args:
            video_data: Binary video data
            project_id: The project ID
            filename: Optional filename (if None, a unique name will be generated)
            
        Returns:
            The path to the saved video file
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"video_{timestamp}_{uuid.uuid4().hex[:6]}.mp4"
        
        # Ensure the extension is included
        if not filename.lower().endswith(('.mp4', '.mov', '.avi')):
            filename += '.mp4'
        
        project_video_dir = self.assets_dir / project_id / "video"
        video_path = project_video_dir / filename
        
        try:
            with open(video_path, 'wb') as f:
                f.write(video_data)
            
            logger.debug(f"Saved video to {video_path}")
            return str(video_path)
        except Exception as e:
            logger.error(f"Error saving video {filename}: {str(e)}")
            raise
    
    def save_project_metadata(self, project_id: str, metadata: Dict[str, Any]) -> str:
        """
        Save project metadata to a JSON file.
        
        Args:
            project_id: The project ID
            metadata: Dictionary containing project metadata
            
        Returns:
            The path to the saved metadata file
        """
        project_dir = self.assets_dir / project_id
        metadata_path = project_dir / "metadata.json"
        
        # Add timestamp to metadata
        metadata['timestamp'] = datetime.now().isoformat()
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.debug(f"Saved project metadata to {metadata_path}")
            return str(metadata_path)
        except Exception as e:
            logger.error(f"Error saving project metadata: {str(e)}")
            raise
    
    def save_tracking_data(self, tracking_data: Dict[str, Any], filename: str = None) -> str:
        """
        Save tracking data to the output tracking directory.
        
        Args:
            tracking_data: Dictionary containing tracking data
            filename: Optional filename (if None, a unique name will be generated)
            
        Returns:
            The path to the saved tracking file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tracking_{timestamp}.json"
        
        # Ensure the extension is included
        if not filename.endswith('.json'):
            filename += '.json'
        
        tracking_path = self.output_tracking_dir / filename
        
        # Add timestamp to tracking data
        tracking_data['saved_at'] = datetime.now().isoformat()
        
        try:
            with open(tracking_path, 'w') as f:
                json.dump(tracking_data, f, indent=2)
            
            logger.debug(f"Saved tracking data to {tracking_path}")
            return str(tracking_path)
        except Exception as e:
            logger.error(f"Error saving tracking data: {str(e)}")
            raise
    
    def load_tracking_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load tracking data from the output tracking directory.
        
        Args:
            filename: The filename of the tracking data file
            
        Returns:
            Dictionary containing tracking data or None if file doesn't exist
        """
        # Ensure the extension is included
        if not filename.endswith('.json'):
            filename += '.json'
        
        tracking_path = self.output_tracking_dir / filename
        
        if not tracking_path.exists():
            logger.warning(f"Tracking data file not found: {tracking_path}")
            return None
        
        try:
            with open(tracking_path, 'r') as f:
                tracking_data = json.load(f)
            
            logger.debug(f"Loaded tracking data from {tracking_path}")
            return tracking_data
        except Exception as e:
            logger.error(f"Error loading tracking data: {str(e)}")
            return None
    
    def get_all_tracking_files(self) -> List[str]:
        """
        Get a list of all tracking data files.
        
        Returns:
            List of filenames for all tracking data files
        """
        tracking_files = [f.name for f in self.output_tracking_dir.glob('*.json')]
        tracking_files.sort(reverse=True)  # Most recent first
        return tracking_files
    
    def cleanup_project(self, project_id: str, keep_final_video: bool = True) -> bool:
        """
        Clean up a project directory, optionally keeping the final video.
        
        Args:
            project_id: The project ID
            keep_final_video: Whether to keep the final video file
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        project_dir = self.assets_dir / project_id
        
        if not project_dir.exists():
            logger.warning(f"Project directory not found: {project_dir}")
            return False
        
        try:
            # If we want to keep the final video, move it to the main video directory
            if keep_final_video:
                project_video_dir = project_dir / "video"
                
                # Find the most recent video file
                video_files = list(project_video_dir.glob('*.mp4'))
                if video_files:
                    video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    final_video = video_files[0]
                    
                    # Move the final video to the main video directory
                    dest_video = self.video_dir / final_video.name
                    shutil.copy2(final_video, dest_video)
                    logger.info(f"Kept final video: {dest_video}")
            
            # Remove the project directory
            shutil.rmtree(project_dir)
            logger.info(f"Cleaned up project directory: {project_dir}")
            
            return True
        except Exception as e:
            logger.error(f"Error cleaning up project {project_id}: {str(e)}")
            return False
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Get disk usage statistics for the data directories.
        
        Returns:
            Dictionary with disk usage information
        """
        def get_dir_size(path: Path) -> int:
            total_size = 0
            if path.exists():
                for entry in path.glob('**/*'):
                    if entry.is_file():
                        total_size += entry.stat().st_size
            return total_size
        
        # Calculate sizes in bytes
        image_size = get_dir_size(self.image_dir)
        audio_size = get_dir_size(self.audio_dir)
        video_size = get_dir_size(self.video_dir)
        project_size = get_dir_size(self.assets_dir) - image_size - audio_size - video_size
        total_size = image_size + audio_size + video_size + project_size
        
        # Convert to MB for readability
        to_mb = lambda bytes: round(bytes / (1024 * 1024), 2)
        
        return {
            "total_mb": to_mb(total_size),
            "images_mb": to_mb(image_size),
            "audio_mb": to_mb(audio_size),
            "videos_mb": to_mb(video_size),
            "projects_mb": to_mb(project_size),
            "assets_dir": str(self.assets_dir)
        }