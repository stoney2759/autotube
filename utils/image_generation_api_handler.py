"""
Image generation API handler for YouTube Shorts Automation System using DALL-E.
"""
import logging
import requests
import base64
from typing import List, Dict, Any, Optional
import os

from utils.error_handling import APIError, retry

logger = logging.getLogger(__name__)

class ImageGenerationAPIHandler:
    """Handler for DALL-E image generation API interactions."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """
        Initialize the DALL-E image generation API handler.
        
        Args:
            api_key: OpenAI API key
            api_base: Base URL for the API (optional)
        """
        # Use environment variable as a fallback for API key
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        if not self.api_key:
            raise APIError("No OpenAI API key provided. Set OPENAI_API_KEY environment variable or pass api_key.")
        
        # Set default DALL-E API base URL
        self.api_base = api_base or "https://api.openai.com/v1/images/generations"
        
        # Create a session for API requests
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        logger.info("Initialized DALL-E image generation API handler")
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        style: str = "photorealistic"
    ) -> List[bytes]:
        """
        Generate images using DALL-E API.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to include
            width: Image width (DALL-E has specific size requirements)
            height: Image height 
            num_images: Number of images to generate
            style: Style to apply (note: DALL-E has limited style control)
            
        Returns:
            List of image data as bytes
            
        Raises:
            APIError: If image generation fails
        """
        # Validate and adjust dimensions for DALL-E
        # DALL-E 3 supports: 1024x1024, 1024x1792, 1792x1024
        if width > height:
            size = "1792x1024"
        elif height > width:
            size = "1024x1792"
        else:
            size = "1024x1024"
        
        # Integrate negative prompt into main prompt for DALL-E
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f". Avoid the following: {negative_prompt}"
        
        # Prepare payload
        payload = {
            "model": "dall-e-3",  # Using the latest DALL-E model
            "prompt": full_prompt,
            "n": 1,  # DALL-E 3 only supports 1 image per request
            "size": size,
            "quality": "standard"  # or "hd" for higher quality
        }
        
        logger.info(f"Generating image with DALL-E: {full_prompt}")
        
        try:
            # Generate the requested number of images
            images = []
            for _ in range(num_images):
                response = self._make_request(
                    method="POST", 
                    url=self.api_base, 
                    json_data=payload
                )
                
                result = response.json()
                
                if "data" not in result or not result["data"]:
                    logger.error(f"Unexpected response format: {result}")
                    raise APIError("No images returned by DALL-E API")
                
                # Download images from URLs
                for item in result["data"]:
                    img_url = item.get("url")
                    if not img_url:
                        logger.warning("Image URL not found in response")
                        continue
                    
                    # Download the image
                    img_response = requests.get(img_url, timeout=30)
                    img_response.raise_for_status()
                    images.append(img_response.content)
            
            logger.info(f"Successfully generated {len(images)} images")
            return images
            
        except Exception as e:
            logger.error(f"Error generating images with DALL-E: {str(e)}")
            raise APIError(f"Image generation failed: {str(e)}") from e
    
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
            raise APIError(f"DALL-E API request failed: {str(e)}") from e