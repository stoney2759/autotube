"""
Image generation API handler for YouTube Shorts Automation System.
"""
import logging
import requests
import base64
from typing import List, Dict, Any, Optional
from utils.error_handling import APIError, retry

logger = logging.getLogger(__name__)

class ImageGenerationAPIHandler:
    """Handler for image generation API interactions."""
    
    def __init__(
        self, 
        provider: str = "stable_diffusion", 
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """
        Initialize the image generation API handler.
        
        Args:
            provider: The image generation provider (stable_diffusion, dalle, etc.)
            api_key: API key for the provider
            api_base: Base URL for the API
        """
        self.api_key = api_key
        self.provider = provider.lower()
        self.api_base = api_base
        self.session = requests.Session()
        
        # Set default API base URLs
        if not self.api_base:
            if self.provider == "stable_diffusion":
                self.api_base = "https://api.stability.ai/v1/generation"
            elif self.provider == "dalle":
                self.api_base = "https://api.openai.com/v1/images/generations"
            else:
                logger.warning(f"Unknown provider: {provider}, API base URL must be provided")
        
        logger.info(f"Initialized image generation API handler for provider: {self.provider}")
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1080,
        height: int = 1920,
        num_images: int = 1,
        style: str = "photorealistic"
    ) -> List[bytes]:
        """
        Generate images based on a prompt.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to include
            width: Image width
            height: Image height
            num_images: Number of images to generate
            style: Style to apply (provider-specific)
            
        Returns:
            List of image data as bytes
            
        Raises:
            APIError: If the image generation fails
        """
        if not self.api_key:
            raise APIError("API key is required for image generation")
        
        if self.provider == "stable_diffusion":
            return self._generate_stable_diffusion(
                prompt, negative_prompt, width, height, num_images, style
            )
        elif self.provider == "dalle":
            return self._generate_dalle(
                prompt, negative_prompt, width, height, num_images, style
            )
        else:
            raise APIError(f"Unsupported provider: {self.provider}")
    
    @retry(max_tries=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _generate_stable_diffusion(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        style: str
    ) -> List[bytes]:
        """
        Generate images using Stable Diffusion API.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to include
            width: Image width
            height: Image height
            num_images: Number of images to generate
            style: Style to apply
            
        Returns:
            List of image data as bytes
        """
        # Ensure width and height are multiples of 64
        width = (width // 64) * 64
        height = (height // 64) * 64
        
        # Map style to engine_id
        engine_id = "stable-diffusion-xl-1024-v1-0"
        if style == "photorealistic":
            engine_id = "stable-diffusion-xl-1024-v1-0"
        elif style == "anime":
            engine_id = "stable-diffusion-anime-1024-v1-0"
        
        url = f"{self.api_base}/{engine_id}/text-to-image"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": num_images,
            "steps": 30
        }
        
        # Add negative prompt if provided
        if negative_prompt:
            payload["text_prompts"].append({
                "text": negative_prompt,
                "weight": -1.0
            })
        
        logger.info(f"Generating {num_images} images with Stable Diffusion: {prompt}")
        
        try:
            response = self._make_request(
                method="POST",
                url=url,
                json_data=payload,
                headers=headers
            )
            
            result = response.json()
            
            if "artifacts" not in result:
                logger.error(f"Unexpected response format: {result}")
                raise APIError(f"Unexpected response from Stable Diffusion API")
            
            # Extract and decode base64 images
            images = []
            for artifact in result["artifacts"]:
                image_data = base64.b64decode(artifact["base64"])
                images.append(image_data)
            
            logger.info(f"Successfully generated {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"Error generating images with Stable Diffusion: {str(e)}")
            raise APIError(f"Error generating images: {str(e)}") from e
    
    @retry(max_tries=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _generate_dalle(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        style: str
    ) -> List[bytes]:
        """
        Generate images using DALL-E API.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to include
            width: Image width
            height: Image height
            num_images: Number of images to generate
            style: Style to apply
            
        Returns:
            List of image data as bytes
        """
        # DALL-E API has specific size requirements
        # Valid sizes: 1024x1024, 1024x1792, 1792x1024
        if width > height:
            size = "1792x1024"
        elif height > width:
            size = "1024x1792"
        else:
            size = "1024x1024"
        
        # DALL-E doesn't directly support negative prompts, so we integrate it
        if negative_prompt:
            full_prompt = f"{prompt}. Please avoid: {negative_prompt}"
        else:
            full_prompt = prompt
        
        # Choose model based on style
        model = "dall-e-3"
        
        url = self.api_base
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "n": min(num_images, 1),  # DALL-E 3 only supports 1 image per request
            "size": size,
            "quality": "standard"
        }
        
        logger.info(f"Generating image with DALL-E: {prompt}")
        
        try:
            images = []
            
            # Make multiple requests if num_images > 1
            for _ in range(num_images):
                response = self._make_request(
                    method="POST",
                    url=url,
                    json_data=payload,
                    headers=headers
                )
                
                result = response.json()
                
                if "data" not in result or not result["data"]:
                    logger.error(f"Unexpected response format: {result}")
                    raise APIError(f"Unexpected response from DALL-E API")
                
                # Download images from URLs
                for item in result["data"]:
                    img_url = item.get("url")
                    if not img_url:
                        continue
                    
                    img_response = requests.get(img_url, timeout=30)
                    img_response.raise_for_status()
                    images.append(img_response.content)
            
            logger.info(f"Successfully generated {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"Error generating images with DALL-E: {str(e)}")
            raise APIError(f"Error generating images: {str(e)}") from e
    
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