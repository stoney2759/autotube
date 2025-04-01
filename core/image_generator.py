"""
Image generation module for YouTube Shorts Automation System.
Connects to image generation APIs and processes images for videos.
"""
import logging
import os
import time
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import io

from utils.error_handling import MediaError, retry, safe_execute
from utils.file_management import FileManager
from utils.image_generation_api_handler import ImageGenerationAPIHandler
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    Handles image generation and processing for video creation.
    """
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        file_manager: FileManager,
        api_handler: Optional[ImageGenerationAPIHandler] = None
    ):
        """
        Initialize the image generator.
        
        Args:
            config_loader: Configuration loader instance
            file_manager: File manager instance
            api_handler: Optional image generation API handler
        """
        self.config = config_loader
        self.file_manager = file_manager
        
        # Load configuration
        self.image_count = self.config.get_config_value("image.count_per_video", 5)
        self.image_style = self.config.get_config_value("image.style", "photorealistic")
        self.resolution = self._parse_resolution(
            self.config.get_config_value("video.resolution", "1024x1024")
        )
        
        # Initialize API handler if not provided
        if not api_handler:
            api_key = self.config.get_api_key("image_generation")
            
            if not api_key:
                logger.warning("No API key found for image generation. Some features will be limited.")
            
            # Create API handler without 'provider' argument
            self.api_handler = ImageGenerationAPIHandler(api_key)
        else:
            self.api_handler = api_handler
        
        logger.info("Image generator initialized")

    def preprocess_images_for_video(self, image_paths: List[str], output_dir: str) -> List[str]:
        """
        Preprocess images to ensure they're compatible with video creation.
        This helps avoid "Operation on closed image" errors.
        
        Args:
            image_paths: List of paths to the images
            output_dir: Directory to save processed images
            
        Returns:
            List of paths to processed images
        """
        if not image_paths:
            return []
        
        processed_paths = []
        
        for i, img_path in enumerate(image_paths):
            try:
                # Create output filename
                filename = f"processed_{i:02d}.jpg"
                output_path = os.path.join(output_dir, filename)
                
                # Open and process image
                with Image.open(img_path) as img:
                    # Convert to RGB (removes alpha channel if present)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save as JPEG (more compatible with video processing)
                    img.save(output_path, 'JPEG', quality=95)
                    
                    processed_paths.append(output_path)
                    logger.debug(f"Preprocessed image: {img_path} -> {output_path}")
            except Exception as e:
                logger.error(f"Error preprocessing image {img_path}: {str(e)}")
                # Fall back to original image
                processed_paths.append(img_path)
        
        return processed_paths
    
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
    
    def generate_images(
        self,
        prompts: List[str],
        project_id: str,
        negative_prompt: str = "",
        retry_attempts: int = 3
    ) -> List[str]:
        """
        Generate images based on prompts.
        
        Args:
            prompts: List of text prompts for image generation
            project_id: Project ID for saving images
            negative_prompt: Negative prompt to guide what not to include
            retry_attempts: Number of retry attempts for failed generations
            
        Returns:
            List of paths to generated images
            
        Raises:
            MediaError: If image generation fails after all retries
        """
        if not prompts:
            raise MediaError("No prompts provided for image generation")
        
        # Get configuration values
        width, height = self.resolution
        
        logger.info(f"Generating {len(prompts)} images for project {project_id}")
        
        image_paths = []
        
        for i, prompt in enumerate(prompts):
            try:
                # Try to generate image with retries
                for attempt in range(retry_attempts):
                    try:
                        logger.debug(f"Generating image {i+1}/{len(prompts)}, attempt {attempt+1}")
                        
                        # Call API to generate image
                        images_data = self.api_handler.generate_image(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=width,
                            height=height,
                            num_images=1,
                            style=self.image_style
                        )
                        
                        if not images_data:
                            logger.warning(f"No images returned for prompt {i+1}")
                            continue
                        
                        # Process and save the image
                        image_data = images_data[0]
                        img_filename = f"image_{i+1:02d}_{int(time.time())}.png"
                        img_path = self.file_manager.save_image(image_data, project_id, img_filename)
                        
                        image_paths.append(img_path)
                        logger.info(f"Successfully generated image {i+1}/{len(prompts)}")
                        
                        # Successfully generated, break the retry loop
                        break
                        
                    except Exception as e:
                        if attempt < retry_attempts - 1:
                            logger.warning(f"Error generating image {i+1}, attempt {attempt+1}: {str(e)}")
                            time.sleep(2 * (attempt + 1))  # Increasing delay between retries
                        else:
                            logger.error(f"Failed to generate image {i+1} after {retry_attempts} attempts: {str(e)}")
                            raise
            except Exception as e:
                logger.error(f"Error generating image for prompt {i+1}: {str(e)}")
                # Continue with next prompt instead of failing completely
                continue
        
        if not image_paths:
            # If all image generations failed, try backup approach
            logger.warning("All image generations failed. Using backup image generation.")
            image_paths = self._generate_backup_images(project_id, len(prompts))
            
            if not image_paths:
                raise MediaError("Failed to generate any images for the project")
        
        logger.info(f"Generated {len(image_paths)} images for project {project_id}")
        return image_paths
    
    def _generate_backup_images(self, project_id: str, count: int) -> List[str]:
        """
        Generate backup images when API-based generation fails.
        Creates simple gradient or color-based images.
        
        Args:
            project_id: Project ID for saving images
            count: Number of images to generate
            
        Returns:
            List of paths to generated images
        """
        logger.info(f"Generating {count} backup images")
        
        width, height = self.resolution
        image_paths = []
        
        # Color schemes for backup images
        color_schemes = [
            [(33, 150, 243), (3, 169, 244), (0, 188, 212)],  # Blue
            [(233, 30, 99), (244, 143, 177), (255, 193, 7)],  # Pink/Yellow
            [(76, 175, 80), (139, 195, 74), (205, 220, 57)],  # Green
            [(156, 39, 176), (103, 58, 183), (63, 81, 181)],  # Purple
            [(255, 87, 34), (255, 152, 0), (255, 193, 7)]     # Orange
        ]
        
        for i in range(count):
            try:
                # Choose a color scheme
                colors = random.choice(color_schemes)
                
                # Create a new image
                img = Image.new('RGB', (width, height), color=colors[0])
                draw = ImageDraw.Draw(img)
                
                # Generate a random pattern
                pattern_type = random.choice(['gradient', 'circles', 'lines'])
                
                if pattern_type == 'gradient':
                    # Create a gradient
                    for y in range(height):
                        r = int(colors[0][0] + (colors[2][0] - colors[0][0]) * y / height)
                        g = int(colors[0][1] + (colors[2][1] - colors[0][1]) * y / height)
                        b = int(colors[0][2] + (colors[2][2] - colors[0][2]) * y / height)
                        draw.line([(0, y), (width, y)], fill=(r, g, b))
                
                elif pattern_type == 'circles':
                    # Draw random circles
                    for _ in range(20):
                        center_x = random.randint(0, width)
                        center_y = random.randint(0, height)
                        radius = random.randint(50, 400)
                        color_idx = random.randint(0, len(colors) - 1)
                        draw.ellipse(
                            [(center_x - radius, center_y - radius), 
                             (center_x + radius, center_y + radius)], 
                            fill=colors[color_idx]
                        )
                
                elif pattern_type == 'lines':
                    # Draw random lines
                    for _ in range(40):
                        start_x = random.randint(0, width)
                        start_y = random.randint(0, height)
                        end_x = random.randint(0, width)
                        end_y = random.randint(0, height)
                        color_idx = random.randint(0, len(colors) - 1)
                        line_width = random.randint(5, 20)
                        draw.line([(start_x, start_y), (end_x, end_y)], 
                                 fill=colors[color_idx], width=line_width)
                
                # Apply a blur for softer look
                img = img.filter(ImageFilter.GaussianBlur(radius=5))
                
                # Add text indication that this is a backup image
                try:
                    # Try to load a font, fall back to default if not available
                    font = ImageFont.truetype("arial.ttf", 40)
                except IOError:
                    font = ImageFont.load_default()
                
                draw = ImageDraw.Draw(img)
                text = f"Generated Image {i+1}"
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                text_x = (width - text_width) // 2
                text_y = (height - text_height) // 2
                
                # Draw text with shadow for visibility
                draw.text((text_x+2, text_y+2), text, font=font, fill=(0, 0, 0, 128))
                draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
                
                # Save the image
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                img_filename = f"backup_image_{i+1:02d}_{int(time.time())}.png"
                img_path = self.file_manager.save_image(img_bytes.read(), project_id, img_filename)
                
                image_paths.append(img_path)
                logger.info(f"Generated backup image {i+1}/{count}")
                
            except Exception as e:
                logger.error(f"Error generating backup image {i+1}: {str(e)}")
                # Continue with next image
        
        return image_paths
    
    def process_images(
        self,
        image_paths: List[str],
        project_id: str,
        add_text: Optional[List[str]] = None,
        add_watermark: bool = False
    ) -> List[str]:
        """
        Process images by adding text, watermarks, or other effects.
        
        Args:
            image_paths: List of paths to images
            project_id: Project ID for saving processed images
            add_text: Optional list of text to add to each image
            add_watermark: Whether to add a watermark
            
        Returns:
            List of paths to processed images
        """
        if not image_paths:
            logger.warning("No images provided for processing")
            return []
        
        logger.info(f"Processing {len(image_paths)} images")
        
        processed_paths = []
        
        for i, img_path in enumerate(image_paths):
            try:
                # Open the image
                with Image.open(img_path) as img:
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Add text if provided
                    if add_text and i < len(add_text) and add_text[i]:
                        img = self._add_text_to_image(img, add_text[i])
                    
                    # Add watermark if requested
                    if add_watermark:
                        img = self._add_watermark(img)
                    
                    # Save the processed image
                    processed_filename = f"processed_{os.path.basename(img_path)}"
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    processed_path = self.file_manager.save_image(
                        img_bytes.read(), project_id, processed_filename
                    )
                    
                    processed_paths.append(processed_path)
                    logger.debug(f"Processed image {i+1}/{len(image_paths)}")
                    
            except Exception as e:
                logger.error(f"Error processing image {i+1}: {str(e)}")
                # Use the original image as fallback
                processed_paths.append(img_path)
        
        logger.info(f"Processed {len(processed_paths)} images")
        return processed_paths
    
    def _add_text_to_image(self, img: Image.Image, text: str) -> Image.Image:
        """
        Add text to an image.
        
        Args:
            img: PIL Image
            text: Text to add
            
        Returns:
            Modified PIL Image
        """
        # Create a copy to avoid modifying the original
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except IOError:
            font = ImageFont.load_default()
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        padding = 20
        text_x = padding
        text_y = img.height - text_height - padding
        
        # Draw text with background for visibility
        text_bg_bbox = (
            text_x - padding//2,
            text_y - padding//2,
            text_x + text_width + padding//2,
            text_y + text_height + padding//2
        )
        draw.rectangle(text_bg_bbox, fill=(0, 0, 0, 128))
        
        # Draw text
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        
        return img_copy
    
    def _add_watermark(self, img: Image.Image, watermark_text: str = None) -> Image.Image:
        """
        Add a watermark to an image.
        
        Args:
            img: PIL Image
            watermark_text: Optional custom watermark text
            
        Returns:
            Modified PIL Image
        """
        # Create a copy to avoid modifying the original
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Set watermark text
        if not watermark_text:
            watermark_text = self.config.get_config_value("content.watermark_text", "Generated Video")
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            font = ImageFont.load_default()
        
        # Calculate text position (bottom right corner)
        text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        padding = 10
        text_x = img.width - text_width - padding
        text_y = img.height - text_height - padding
        
        # Draw semi-transparent text for watermark
        draw.text((text_x+1, text_y+1), watermark_text, font=font, fill=(0, 0, 0, 128))
        draw.text((text_x, text_y), watermark_text, font=font, fill=(255, 255, 255, 180))
        
        return img_copy
    
    def resize_image(self, img_path: str, output_path: str, width: int, height: int) -> str:
        """
        Resize an image to the specified dimensions.
        
        Args:
            img_path: Path to the input image
            output_path: Path to save the resized image
            width: Target width
            height: Target height
            
        Returns:
            Path to the resized image
            
        Raises:
            MediaError: If image resizing fails
        """
        try:
            with Image.open(img_path) as img:
                # Determine if we need to crop or pad to maintain aspect ratio
                img_ratio = img.width / img.height
                target_ratio = width / height
                
                if img_ratio > target_ratio:
                    # Image is wider than target, crop width
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) // 2
                    img_resized = img.crop((left, 0, left + new_width, img.height))
                    img_resized = img_resized.resize((width, height), Image.Resampling.LANCZOS)
                elif img_ratio < target_ratio:
                    # Image is taller than target, crop height
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) // 2
                    img_resized = img.crop((0, top, img.width, top + new_height))
                    img_resized = img_resized.resize((width, height), Image.Resampling.LANCZOS)
                else:
                    # Same ratio, just resize
                    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                
                # Save the resized image
                img_resized.save(output_path)
                
                logger.debug(f"Resized image from {img.width}x{img.height} to {width}x{height}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            raise MediaError(f"Failed to resize image: {str(e)}") from e
    
    def enhance_image(self, img_path: str, output_path: str) -> str:
        """
        Enhance an image's quality by adjusting brightness, contrast, etc.
        
        Args:
            img_path: Path to the input image
            output_path: Path to save the enhanced image
            
        Returns:
            Path to the enhanced image
        """
        try:
            with Image.open(img_path) as img:
                # Adjust brightness slightly
                enhancer = ImageEnhance.Brightness(img)
                img_enhanced = enhancer.enhance(1.1)  # Increase brightness by 10%
                
                # Adjust contrast
                enhancer = ImageEnhance.Contrast(img_enhanced)
                img_enhanced = enhancer.enhance(1.2)  # Increase contrast by 20%
                
                # Adjust color
                enhancer = ImageEnhance.Color(img_enhanced)
                img_enhanced = enhancer.enhance(1.1)  # Increase color saturation by 10%
                
                # Adjust sharpness
                enhancer = ImageEnhance.Sharpness(img_enhanced)
                img_enhanced = enhancer.enhance(1.3)  # Increase sharpness by 30%
                
                # Save the enhanced image
                img_enhanced.save(output_path)
                
                logger.debug(f"Enhanced image quality: {os.path.basename(img_path)}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            # Return original path as fallback
            return img_path