"""
YouTube Upload Module for YouTube Shorts Automation.
Handles authentication and uploading to YouTube.
"""
import logging
import os
import yaml
import json
import time
import http.client
import httplib2
import random
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from datetime import datetime, timedelta

class YouTubeUploader:
    """
    Handles authentication and uploading videos to YouTube.
    """
    
    def __init__(self, config_path='config/config.yaml', api_keys_path='config/api_keys.yaml'):
        """
        Initialize YouTube uploader with configuration
        
        Args:
            config_path (str): Path to configuration file
            api_keys_path (str): Path to API keys file
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing YouTube Uploader")
        
        # Load configuration
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            self.logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {
                'uploader': {
                    'privacy_status': 'private',  # Default to private uploads
                    'tags_limit': 500,  # Character limit for tags
                    'retry_count': 3,   # Number of upload retry attempts
                    'retry_delay': 5    # Delay between retries in seconds
                }
            }
            self.logger.warning("Using default uploader configuration")
        
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
        
        # Initialize YouTube API
        self.youtube = None
        self.authenticated = False
    
    def authenticate(self):
        """
        Authenticate with YouTube API
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Get YouTube API credentials
            youtube_creds = self.api_keys.get('youtube', {})
            client_id = youtube_creds.get('client_id')
            client_secret = youtube_creds.get('client_secret')
            refresh_token = youtube_creds.get('refresh_token')
            
            if not client_id or not client_secret or not refresh_token:
                self.logger.error("Missing YouTube API credentials")
                return False
            
            # Create credentials object
            credentials = google.oauth2.credentials.Credentials(
                None,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri="https://oauth2.googleapis.com/token"
            )
            
            # Build YouTube API service
            self.youtube = googleapiclient.discovery.build(
                "youtube", "v3", credentials=credentials,
                cache_discovery=False
            )
            
            # Test API connection
            channels_response = self.youtube.channels().list(
                part="snippet",
                mine=True
            ).execute()
            
            channel_title = channels_response["items"][0]["snippet"]["title"]
            self.logger.info(f"Successfully authenticated with YouTube as: {channel_title}")
            
            self.authenticated = True
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.authenticated = False
            return False
    
    def upload_video(self, video_path, metadata=None):
        """
        Upload a video to YouTube
        
        Args:
            video_path (str): Path to the video file
            metadata (dict, optional): Video metadata
            
        Returns:
            dict: Upload result with status and video ID
        """
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": "Video file not found"}
        
        # Ensure we're authenticated
        if not self.authenticated:
            success = self.authenticate()
            if not success:
                return {"success": False, "error": "Authentication failed"}
        
        # Initialize metadata if not provided
        if metadata is None:
            metadata = {}
        
        try:
            # Prepare video metadata
            uploader_config = self.config.get('uploader', {})
            
            # Default privacy status
            privacy_status = metadata.get('privacyStatus', 
                                        uploader_config.get('privacy_status', 'private'))
            
            # Process tags (limit total character count)
            tags = metadata.get('tags', [])
            if tags:
                tags_limit = uploader_config.get('tags_limit', 500)
                filtered_tags = []
                char_count = 0
                
                for tag in tags:
                    # Add comma for character count calculation
                    tag_len = len(tag) + 1
                    if char_count + tag_len <= tags_limit:
                        filtered_tags.append(tag)
                        char_count += tag_len
                    else:
                        break
                
                tags = filtered_tags
            
            # Get video category ID
            category_id = metadata.get('category', '22')  # 22 = People & Blogs (default)
            
            # Create video insert request body
            body = {
                "snippet": {
                    "title": metadata.get('title', 'YouTube Short'),
                    "description": metadata.get('description', ''),
                    "tags": tags,
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Create upload request
            media_file = googleapiclient.http.MediaFileUpload(
                video_path,
                chunksize=1024*1024,
                resumable=True
            )
            
            # Create insert request
            insert_request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media_file
            )
            
            self.logger.info(f"Starting upload of {video_path}")
            
            # Upload the video with progress tracking and retry logic
            response = self._resumable_upload(insert_request)
            
            # Return upload result
            return response
            
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def _resumable_upload(self, insert_request):
        """
        Resumable upload implementation with retry logic
        
        Args:
            insert_request: YouTube API insert request
            
        Returns:
            dict: Upload result with status and video ID
        """
        uploader_config = self.config.get('uploader', {})
        retry_count = uploader_config.get('retry_count', 3)
        retry_delay = uploader_config.get('retry_delay', 5)
        
        response = None
        error = None
        retry = 0
        
        while response is None and retry <= retry_count:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.info(f"Upload progress: {progress}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retry on server errors
                    error = f"Server error during upload: {e.resp.status}"
                    retry += 1
                    if retry <= retry_count:
                        time.sleep(retry_delay)
                        continue
                else:
                    error = f"HTTP error during upload: {e.resp.status}"
                    break
            except (httplib2.HttpLib2Error, IOError) as e:
                # Retry on connection errors
                error = f"Connection error during upload: {str(e)}"
                retry += 1
                if retry <= retry_count:
                    time.sleep(retry_delay)
                    continue
                else:
                    break
        
        if response:
            video_id = response.get('id')
            self.logger.info(f"Video uploaded successfully. ID: {video_id}")
            return {
                "success": True,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }
        else:
            self.logger.error(f"Upload failed: {error}")
            return {"success": False, "error": error}
    
    def add_to_playlist(self, video_id, playlist_id):
        """
        Add a video to a YouTube playlist
        
        Args:
            video_id (str): YouTube video ID
            playlist_id (str): YouTube playlist ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.authenticated:
            success = self.authenticate()
            if not success:
                return False
        
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            ).execute()
            
            self.logger.info(f"Added video {video_id} to playlist {playlist_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding video to playlist: {e}")
            return False
    
    def get_upload_status(self, video_id):
        """
        Get the status of an uploaded video
        
        Args:
            video_id (str): YouTube video ID
            
        Returns:
            dict: Video status information
        """
        if not self.authenticated:
            success = self.authenticate()
            if not success:
                return {"success": False, "error": "Authentication failed"}
        
        try:
            response = self.youtube.videos().list(
                part="status,processingDetails",
                id=video_id
            ).execute()
            
            if not response.get("items"):
                return {"success": False, "error": "Video not found"}
            
            video_status = response["items"][0]
            return {
                "success": True,
                "status": video_status.get("status", {}),
                "processing": video_status.get("processingDetails", {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting video status: {e}")
            return {"success": False, "error": str(e)}
    
    def update_video_metadata(self, video_id, metadata):
        """
        Update metadata for an existing video
        
        Args:
            video_id (str): YouTube video ID
            metadata (dict): Updated video metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.authenticated:
            success = self.authenticate()
            if not success:
                return False
        
        try:
            # Fetch current video data
            current_data = self.youtube.videos().list(
                part="snippet,status",
                id=video_id
            ).execute()
            
            if not current_data.get("items"):
                self.logger.error(f"Video not found: {video_id}")
                return False
            
            # Get the current snippet
            current_snippet = current_data["items"][0]["snippet"]
            
            # Update with new metadata
            updated_snippet = current_snippet.copy()
            
            if 'title' in metadata:
                updated_snippet["title"] = metadata["title"]
            
            if 'description' in metadata:
                updated_snippet["description"] = metadata["description"]
            
            if 'tags' in metadata:
                updated_snippet["tags"] = metadata["tags"]
            
            if 'category' in metadata:
                updated_snippet["categoryId"] = metadata["category"]
            
            # Update the video
            self.youtube.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": updated_snippet
                }
            ).execute()
            
            # Update privacy status if provided
            if 'privacyStatus' in metadata:
                self.youtube.videos().update(
                    part="status",
                    body={
                        "id": video_id,
                        "status": {
                            "privacyStatus": metadata["privacyStatus"]
                        }
                    }
                ).execute()
            
            self.logger.info(f"Updated metadata for video {video_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating video metadata: {e}")
            return False