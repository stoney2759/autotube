"""
Test script for image generation API.
Verifies API key and connection to the service.
"""
import os
import sys
import yaml
import logging
import requests
import base64
from datetime import datetime
from PIL import Image
import io

# Setup basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_api_keys(api_keys_path='config/api_keys.yaml'):
    """Load API keys from configuration file."""
    try:
        with open(api_keys_path, 'r') as file:
            api_keys = yaml.safe_load(file)
            logger.info(f"Loaded API keys from {api_keys_path}")
            return api_keys
    except Exception as e:
        logger.error(f"Failed to load API keys: {e}")
        return {}

def test_stable_diffusion_api(api_key, api_base=None):
    """Test Stable Diffusion API connection."""
    if not api_base:
        api_base = "https://api.stability.ai/v1/generation"
    
    # Use stable-diffusion-xl-1024-v1-0 engine
    engine_id = "stable-diffusion-xl-1024-v1-0"
    url = f"{api_base}/{engine_id}/text-to-image"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Simple test prompt
    payload = {
        "text_prompts": [
            {
                "text": "A beautiful landscape with mountains and a lake, digital art style",
                "weight": 1.0
            }
        ],
        "cfg_scale": 7,
        "height": 512,  # Smaller size for testing
        "width": 512,
        "samples": 1,
        "steps": 30
    }
    
    logger.info(f"Testing Stable Diffusion API connection to {url}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        if "artifacts" not in result:
            logger.error(f"Unexpected response format: {result}")
            return False, "Unexpected response format"
        
        # Save the generated image
        artifacts = result["artifacts"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        
        for i, artifact in enumerate(artifacts):
            image_data = base64.b64decode(artifact["base64"])
            output_path = os.path.join(output_dir, f"test_image_{timestamp}_{i}.png")
            
            # Save the image
            with open(output_path, "wb") as f:
                f.write(image_data)
            
            # Display info about saved image
            img = Image.open(io.BytesIO(image_data))
            logger.info(f"Generated image saved to {output_path} (Size: {img.size})")
        
        logger.info("Stable Diffusion API test successful!")
        return True, output_path
    
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        
        # Log more detailed error info if available
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                logger.error(f"Error details: {error_details}")
            except:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
        
        return False, str(e)

def test_dalle_api(api_key, api_base=None):
    """Test DALL-E API connection."""
    if not api_base:
        api_base = "https://api.openai.com/v1/images/generations"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "dall-e-3",
        "prompt": "A beautiful landscape with mountains and a lake, digital art style",
        "n": 1,
        "size": "1024x1024",
        "quality": "standard"
    }
    
    logger.info(f"Testing DALL-E API connection to {api_base}")
    
    try:
        response = requests.post(api_base, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        if "data" not in result or not result["data"]:
            logger.error(f"Unexpected response format: {result}")
            return False, "Unexpected response format"
        
        # Get the image URL and download the image
        img_url = result["data"][0].get("url")
        if not img_url:
            logger.error("No image URL in response")
            return False, "No image URL in response"
        
        # Download the image
        img_response = requests.get(img_url, timeout=30)
        img_response.raise_for_status()
        
        # Save the generated image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"test_image_{timestamp}.png")
        
        with open(output_path, "wb") as f:
            f.write(img_response.content)
        
        # Display info about saved image
        img = Image.open(io.BytesIO(img_response.content))
        logger.info(f"Generated image saved to {output_path} (Size: {img.size})")
        
        logger.info("DALL-E API test successful!")
        return True, output_path
    
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        
        # Log more detailed error info if available
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                logger.error(f"Error details: {error_details}")
            except:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
        
        return False, str(e)

def main():
    """Main function to run the tests."""
    logger.info("Starting API key test...")
    
    # Load API keys
    api_keys = load_api_keys()
    
    if not api_keys:
        logger.error("No API keys loaded. Check your config/api_keys.yaml file.")
        sys.exit(1)
    
    # Get image generation config
    image_gen_config = api_keys.get('image_generation', {})
    provider = image_gen_config.get('provider', '').lower()
    api_key = image_gen_config.get('api_key')
    api_base = image_gen_config.get('api_base')
    
    if not provider:
        logger.error("No image generation provider specified in config.")
        sys.exit(1)
    
    if not api_key:
        logger.error("No API key found for image generation.")
        sys.exit(1)
    
    # Test the appropriate API
    success = False
    output_path = None
    
    if provider == "stable_diffusion":
        logger.info("Testing Stable Diffusion API...")
        success, output_path = test_stable_diffusion_api(api_key, api_base)
    elif provider == "dalle":
        logger.info("Testing DALL-E API...")
        success, output_path = test_dalle_api(api_key, api_base)
    else:
        logger.error(f"Unsupported provider: {provider}")
        sys.exit(1)
    
    # Report results
    if success:
        logger.info(f"API test successful! Test image saved to: {output_path}")
        
        # Try to open the image if on Windows
        try:
            if os.name == 'nt':  # Windows
                os.startfile(output_path)
            elif sys.platform == 'darwin':  # macOS
                import subprocess
                subprocess.call(['open', output_path])
            elif os.name == 'posix':  # Linux
                import subprocess
                subprocess.call(['xdg-open', output_path])
        except Exception as e:
            logger.warning(f"Could not open the image: {e}")
    else:
        logger.error(f"API test failed: {output_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()