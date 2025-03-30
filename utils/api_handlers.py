"""
API connection handlers for YouTube Shorts Automation System.
Manages connections to external APIs and handles authentication.
"""
import logging
import time
import json
import os
from typing import Dict, Any, Optional, Callable, List, Union
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from utils.error_handling import APIError, retry

logger = logging.getLogger(__name__)

class APIHandler:
    """Base class for API handlers."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API handler.
        
        Args:
            api_key: Optional API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    def check_rate_limit(self) -> bool:
        """
        Check if rate limit is reached.
        
        Returns:
            True if requests can be made, False if rate limited
        """
        # If rate limit info isn't available, assume we're good
        if self.rate_limit_remaining is None or self.rate_limit_reset is None:
            return True
        
        # If we have requests remaining, we're good
        if self.rate_limit_remaining > 0:
            return True
        
        # If we're rate limited, check if the reset time has passed
        current_time = time.time()
        if current_time >= self.rate_limit_reset:
            # Reset time has passed, reset the rate limit info
            self.rate_limit_remaining = None
            self.rate_limit_reset = None
            return True
        
        # Still rate limited
        wait_time = self.rate_limit_reset - current_time
        logger.warning(f"Rate limited. Reset in {wait_time:.2f} seconds")
        return False
    
    def update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit information from response headers.
        
        Args:
            headers: Response headers
        """
        # This is a placeholder - implement in subclasses based on API specifics
        pass
    
    @retry(max_tries=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def make_request(
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
        # Check rate limits
        if not self.check_rate_limit():
            wait_time = max(1, self.rate_limit_reset - time.time())
            logger.info(f"Waiting for rate limit reset: {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        # Set up default headers
        if headers is None:
            headers = {}
        
        # Add API key to params if it exists and isn't already in params
        if self.api_key and params is None:
            params = {}
        if self.api_key and 'api_key' not in params and 'key' not in params:
            params['api_key'] = self.api_key
        
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
            
            # Update rate limit information
            self.update_rate_limit_info(response.headers)
            
            # Check for HTTP errors
            response.raise_for_status()
            
            return response
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise APIError(f"API request failed: {str(e)}") from e


class YouTubeAPIHandler:
    """Handler for YouTube API interactions."""
    
    # Define OAuth scopes
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.force-ssl'
    ]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_file: str = "config/youtube_token.json",
        credentials_file: Optional[str] = None
    ):
        """
        Initialize the YouTube API handler.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            refresh_token: OAuth refresh token
            token_file: Path to save/load token
            credentials_file: Path to client secrets file
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.credentials = None
        self.service = None
        
        logger.debug("Initialized YouTube API handler")
    
    def authenticate(self) -> bool:
        """
        Authenticate with the YouTube API.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        creds = None
        
        # Try to load credentials from token file
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
                    logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.warning(f"Error loading token file: {str(e)}")
        
        # If credentials are provided directly, use them
        if creds is None and self.client_id and self.client_secret and self.refresh_token:
            creds = Credentials(
                None,  # No access token
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )
            logger.info("Created credentials from provided tokens")
        
        # If credentials expired, refresh them
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed expired credentials")
            except RefreshError as e:
                logger.error(f"Error refreshing credentials: {str(e)}")
                creds = None
        
        # If no valid credentials yet, run the OAuth flow
        if not creds and self.credentials_file:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new credentials from OAuth flow")
            except Exception as e:
                logger.error(f"Error running OAuth flow: {str(e)}")
                return False
        
        # If still no credentials, we can't proceed
        if not creds:
            logger.error("Could not obtain valid credentials")
            return False
        
        # Save the credentials for next run
        try:
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Saved credentials to {self.token_file}")
        except Exception as e:
            logger.warning(f"Error saving credentials: {str(e)}")
        
        # Store credentials and build service
        self.credentials = creds
        self.service = build('youtube', 'v3', credentials=creds)
        
        logger.info("Successfully authenticated with YouTube API")
        return True
    
    @retry(max_tries=3, delay=2.0, backoff=2.0, exceptions=(HttpError,))
    def upload_video(
        self, 
        file_path: str, 
        title: str, 
        description: str, 
        tags: List[str],
        category_id: str = "22",  # 22 is "People & Blogs"
        privacy_status: str = "private",  # Start as private, can change later
        notify_subscribers: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a video to YouTube.
        
        Args:
            file_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: Privacy status (private, unlisted, public)
            notify_subscribers: Whether to notify subscribers
            
        Returns:
            Dictionary with video details
            
        Raises:
            APIError: If the upload fails
        """
        if not self.service:
            if not self.authenticate():
                raise APIError("Cannot upload video - not authenticated with YouTube API")
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            # Prepare the request body
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False,
                }
            }
            
            # Create a media upload object
            media = MediaFileUpload(
                file_path,
                mimetype='video/*',
                resumable=True
            )
            
            # Call the API's videos.insert method
            insert_request = self.service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers
            )
            
            logger.info(f"Starting upload of {file_path}")
            response = None
            
            # Upload with progress tracking
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            logger.info(f"Video uploaded successfully: {response['id']}")
            
            return {
                'video_id': response['id'],
                'title': title,
                'privacy_status': privacy_status,
                'url': f"https://www.youtube.com/watch?v={response['id']}"
            }
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise APIError(f"YouTube API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise APIError(f"Error uploading video: {str(e)}") from e
    
    def get_channel_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated user's channel.
        
        Returns:
            Dictionary with channel details
            
        Raises:
            APIError: If the request fails
        """
        if not self.service:
            if not self.authenticate():
                raise APIError("Cannot get channel info - not authenticated with YouTube API")
        
        try:
            # Get the authenticated user's channel
            request = self.service.channels().list(
                part="snippet,statistics,contentDetails",
                mine=True
            )
            response = request.execute()
            
            if not response.get('items'):
                raise APIError("No channel found for authenticated user")
            
            channel = response['items'][0]
            
            return {
                'channel_id': channel['id'],
                'title': channel['snippet']['title'],
                'description': channel['snippet'].get('description', ''),
                'subscribers': channel['statistics'].get('subscriberCount', '0'),
                'views': channel['statistics'].get('viewCount', '0'),
                'videos': channel['statistics'].get('videoCount', '0')
            }
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise APIError(f"YouTube API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error getting channel info: {str(e)}")
            raise APIError(f"Error getting channel info: {str(e)}") from e