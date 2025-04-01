"""
Content generator for YouTube Shorts Automation System.
Sources content ideas from databases/spreadsheets and generates prompts.
"""
import logging
import random
import re
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from string import Template

from utils.error_handling import ContentError, retry, safe_execute
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class ContentGenerator:
    """
    Generates content ideas and prompts for videos from spreadsheets or local sources.
    """
    
    def __init__(
        self, 
        config_loader: ConfigLoader,
        content_db_path: str = "data/content_db",
        use_google_sheets: bool = True
    ):
        """
        Initialize the content generator.
        
        Args:
            config_loader: Configuration loader instance
            content_db_path: Path to local content database
            use_google_sheets: Whether to use Google Sheets as content source
        """
        self.config = config_loader
        self.content_db_path = content_db_path
        self.use_google_sheets = use_google_sheets
        self.sheets_client = None
        
        # Ensure content database directory exists
        os.makedirs(content_db_path, exist_ok=True)
        
        # Initialize Google Sheets connection if enabled
        if use_google_sheets:
            self._init_google_sheets()
        
        logger.info("Content generator initialized")
    
    def _init_google_sheets(self) -> None:
        """
        Initialize Google Sheets API connection.
        
        Raises:
            ContentError: If Google Sheets initialization fails
        """
        try:
            # Check for credentials in api_keys
            gs_creds_file = self.config.get_config_value("content.google_sheets_credentials_file")
            
            if not gs_creds_file or not os.path.exists(gs_creds_file):
                logger.warning("Google Sheets credentials file not found. Google Sheets integration will be disabled.")
                self.use_google_sheets = False
                return
            
            # Scope needed for Google Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Authenticate
            credentials = Credentials.from_service_account_file(gs_creds_file, scopes=scopes)
            self.sheets_client = gspread.authorize(credentials)
            
            logger.info("Google Sheets API initialized")
        except Exception as e:
            logger.warning(f"Unable to initialize Google Sheets: {str(e)}")
            logger.info("Google Sheets integration will be disabled.")
            self.use_google_sheets = False
    
    def get_content_idea(self, theme: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a content idea from the database.
        
        Args:
            theme: Optional theme to filter ideas by
            
        Returns:
            Dictionary containing content idea information
            
        Raises:
            ContentError: If no suitable content ideas are available
        """
        # Try Google Sheets first if enabled
        if self.use_google_sheets and self.sheets_client:
            try:
                idea = self._get_idea_from_sheets(theme)
                if idea:
                    return idea
            except Exception as e:
                logger.error(f"Error getting idea from Google Sheets: {str(e)}")
                logger.warning("Falling back to local content database")
        
        # Fall back to local database
        idea = self._get_idea_from_local(theme)
        if not idea:
            # If no theme-specific idea found, try without theme filter
            if theme:
                logger.warning(f"No ideas found for theme '{theme}'. Trying any theme.")
                idea = self._get_idea_from_local()
        
        if not idea:
            # Last resort: generate a very basic generic idea
            logger.warning("No content ideas available in database. Generating a basic idea.")
            idea = self._generate_backup_idea()
        
        return idea
    
    @retry(max_tries=3, delay=2.0, exceptions=(Exception,))
    def _get_idea_from_sheets(self, theme: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a content idea from Google Sheets.
        
        Args:
            theme: Optional theme to filter ideas by
            
        Returns:
            Dictionary containing content idea or None if no suitable idea found
        """
        # Get spreadsheet ID from config
        spreadsheet_id = self.config.get_config_value("content.spreadsheet_id")
        if not spreadsheet_id:
            logger.error("No spreadsheet_id configured for content")
            return None
        
        try:
            # Open the spreadsheet
            sheet = self.sheets_client.open_by_key(spreadsheet_id).sheet1
            
            # Get all records
            records = sheet.get_all_records()
            if not records:
                logger.warning("No records found in content spreadsheet")
                return None
            
            # Filter by theme if specified
            if theme:
                theme_records = [r for r in records if r.get('theme', '').lower() == theme.lower()]
                if theme_records:
                    records = theme_records
            
            # Filter out used ideas if possible
            unused_records = [r for r in records if r.get('used', False) is not True]
            if unused_records:
                records = unused_records
            
            if not records:
                logger.warning("No unused content ideas available")
                return None
            
            # Select a random record
            selected = random.choice(records)
            
            # Mark as used in the spreadsheet
            if 'used' in selected:
                row_idx = sheet.find(selected.get('title_template', '')).row
                sheet.update_cell(row_idx, sheet.find('used').col, 'TRUE')
                logger.debug(f"Marked idea as used in spreadsheet: {selected.get('title_template', '')}")
            
            # Process the idea to ensure all required fields
            processed_idea = self._process_content_idea(selected)
            
            return processed_idea
            
        except Exception as e:
            logger.error(f"Error getting idea from Google Sheets: {str(e)}")
            raise
    
    def _get_idea_from_local(self, theme: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a content idea from the local database.
        
        Args:
            theme: Optional theme to filter ideas by
            
        Returns:
            Dictionary containing content idea or None if no suitable idea found
        """
        try:
            # Get all JSON files in the content database
            json_files = []
            for root, _, files in os.walk(self.content_db_path):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            
            if not json_files:
                logger.warning(f"No content idea files found in {self.content_db_path}")
                return None
            
            # Load all content ideas
            all_ideas = []
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        file_data = json.load(f)
                        
                        # Handle both single ideas and collections of ideas
                        if isinstance(file_data, list):
                            all_ideas.extend(file_data)
                        else:
                            all_ideas.append(file_data)
                except Exception as e:
                    logger.error(f"Error loading content idea file {json_file}: {str(e)}")
            
            if not all_ideas:
                logger.warning("No valid content ideas found in local database")
                return None
            
            # Filter by theme if specified
            if theme:
                theme_ideas = [idea for idea in all_ideas 
                              if idea.get('theme', '').lower() == theme.lower()]
                if theme_ideas:
                    all_ideas = theme_ideas
            
            # Filter out used ideas if possible
            unused_ideas = [idea for idea in all_ideas if not idea.get('used', False)]
            if unused_ideas:
                all_ideas = unused_ideas
            
            if not all_ideas:
                logger.warning("No unused content ideas available in local database")
                return None
            
            # Select a random idea
            selected = random.choice(all_ideas)
            
            # Mark as used
            selected['used'] = True
            
            # Try to save the updated state
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        file_data = json.load(f)
                    
                    updated = False
                    if isinstance(file_data, list):
                        for i, idea in enumerate(file_data):
                            if (idea.get('title_template') == selected.get('title_template') and
                                idea.get('theme') == selected.get('theme')):
                                file_data[i]['used'] = True
                                updated = True
                                break
                    elif (file_data.get('title_template') == selected.get('title_template') and
                          file_data.get('theme') == selected.get('theme')):
                        file_data['used'] = True
                        updated = True
                    
                    if updated:
                        with open(json_file, 'w') as f:
                            json.dump(file_data, f, indent=2)
                        logger.debug(f"Marked idea as used in {json_file}")
                        break
                except Exception as e:
                    logger.error(f"Error updating content idea file {json_file}: {str(e)}")
            
            # Process the idea to ensure all required fields
            processed_idea = self._process_content_idea(selected)
            
            return processed_idea
            
        except Exception as e:
            logger.error(f"Error getting idea from local database: {str(e)}")
            return None
    
    def _generate_backup_idea(self) -> Dict[str, Any]:
        """
        Generate a basic backup idea when no suitable ideas are found.
        
        Returns:
            Dictionary containing a basic content idea
        """
        # Get default themes from config or use fallbacks
        default_themes = self.config.get_config_value("content.default_themes", 
                                                     ["nature", "technology", "lifestyle", "food"])
        
        # Select a random theme
        theme = random.choice(default_themes)
        
        # Create a basic idea structure
        idea = {
            "theme": theme,
            "title_template": f"Amazing {theme.title()} video that will surprise you",
            "description_template": f"Check out this incredible {theme} content! #shorts #{theme} #trending",
            "keywords": [theme, "amazing", "shorts", "viral"],
            "image_prompts": [f"Beautiful {theme} scene, vibrant colors, high quality, detailed"],
            "used": False,
            "generated": True
        }
        
        logger.info(f"Generated backup idea with theme: {theme}")
        return idea
    
    def _process_content_idea(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a content idea to ensure it has all required fields.
        
        Args:
            idea: Raw content idea
            
        Returns:
            Processed content idea with all required fields
        """
        # Create a copy to avoid modifying the original
        processed = idea.copy()
        
        # Ensure required fields exist
        if 'theme' not in processed:
            processed['theme'] = 'general'
        
        if 'title_template' not in processed:
            processed['title_template'] = f"Amazing {processed['theme'].title()} video"
        
        if 'description_template' not in processed:
            processed['description_template'] = f"Check out this {processed['theme']} content! #shorts #{processed['theme']} #trending"
        
        if 'keywords' not in processed or not processed['keywords']:
            processed['keywords'] = [processed['theme'], 'shorts', 'viral']
        
        if 'image_prompts' not in processed or not processed['image_prompts']:
            processed['image_prompts'] = [f"Beautiful {processed['theme']} scene, vibrant colors"]
        
        # Convert keywords to list if it's a string
        if isinstance(processed['keywords'], str):
            processed['keywords'] = [k.strip() for k in processed['keywords'].split(',')]
        
        # Convert image_prompts to list if it's a string
        if isinstance(processed['image_prompts'], str):
            processed['image_prompts'] = [p.strip() for p in processed['image_prompts'].split('|')]
        
        # Add timestamp
        processed['selected_at'] = datetime.now().isoformat()
        
        return processed
    
    def generate_content_variables(self) -> Dict[str, str]:
        """
        Generate dynamic variables for content templates.
        
        Returns:
            Dictionary of variables for template substitution
        """
        variables = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "year": datetime.now().strftime("%Y"),
            "month": datetime.now().strftime("%B"),
            "day": datetime.now().strftime("%d"),
            "random_number": str(random.randint(1, 100)),
            "random_emoji": random.choice(["✨", "🔥", "⭐", "🚀", "💯", "👀", "🎉", "💥"])
        }
        
        return variables
    
    def apply_templates(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply template substitution to content idea fields.
        
        Args:
            idea: Content idea with templates
            
        Returns:
            Content idea with templates filled in
        """
        # Generate dynamic variables
        variables = self.generate_content_variables()
        
        # Apply template substitution
        result = idea.copy()
        
        if 'title_template' in result:
            title_template = Template(result['title_template'])
            result['title'] = title_template.safe_substitute(variables)
        
        if 'description_template' in result:
            desc_template = Template(result['description_template'])
            result['description'] = desc_template.safe_substitute(variables)
        
        # Process image prompts
        if 'image_prompts' in result:
            processed_prompts = []
            for prompt_template in result['image_prompts']:
                prompt = Template(prompt_template).safe_substitute(variables)
                processed_prompts.append(prompt)
            result['processed_image_prompts'] = processed_prompts
        
        logger.debug(f"Applied templates to content idea: {result.get('title', '')}")
        return result
    
    def generate_video_prompts(
        self,
        idea: Dict[str, Any],
        num_images: int = 5,
        additional_context: str = ""
    ) -> List[str]:
        """
        Generate specific prompts for each image in the video.
        
        Args:
            idea: Content idea
            num_images: Number of image prompts to generate
            additional_context: Additional context for prompt generation
            
        Returns:
            List of image generation prompts
        """
        # Get base prompts from the idea
        base_prompts = idea.get('processed_image_prompts', idea.get('image_prompts', []))
        
        if not base_prompts:
            base_prompts = [f"Beautiful {idea.get('theme', 'content')} scene, vibrant colors"]
        
        # If we don't have enough base prompts, replicate them
        while len(base_prompts) < num_images:
            base_prompts.extend(base_prompts[:num_images-len(base_prompts)])
        
        # Shuffle to mix things up if we're using the same prompt multiple times
        if len(set(base_prompts)) < num_images:
            random.shuffle(base_prompts)
        
        # Take just what we need
        base_prompts = base_prompts[:num_images]
        
        # Enhance prompts with additional context and style guidance
        enhanced_prompts = []
        
        # Get default style from config
        default_style = self.config.get_config_value("image.style", "photorealistic")
        
        style_descriptors = {
            "photorealistic": "photorealistic, high quality, detailed, sharp focus, 8k",
            "anime": "anime style, vibrant colors, clean lines, high quality illustration",
            "artistic": "artistic, painterly style, creative composition, expressive",
            "cinematic": "cinematic, dramatic lighting, film look, movie still",
            "minimalist": "minimalist, clean, simple, elegant composition"
        }
        
        style_suffix = style_descriptors.get(default_style, style_descriptors["photorealistic"])
        
        for i, prompt in enumerate(base_prompts):
            # Add some variation based on position in sequence
            if i == 0:
                enhanced = f"{prompt}, establishing shot, {style_suffix}"
            elif i == num_images - 1:
                enhanced = f"{prompt}, conclusion, final image, {style_suffix}"
            else:
                enhanced = f"{prompt}, {style_suffix}"
            
            # Add additional context if provided
            if additional_context:
                enhanced = f"{enhanced}, {additional_context}"
            
            enhanced_prompts.append(enhanced)
        
        logger.debug(f"Generated {len(enhanced_prompts)} video prompts")
        return enhanced_prompts
    
    def save_idea_locally(self, idea: Dict[str, Any]) -> str:
        """
        Save a content idea to the local database.
        
        Args:
            idea: Content idea to save
            
        Returns:
            Path to the saved file
        """
        # Create a unique filename based on theme and timestamp
        theme = idea.get('theme', 'general').lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{theme}_idea_{timestamp}.json"
        
        # Ensure theme directory exists
        theme_dir = os.path.join(self.content_db_path, theme)
        os.makedirs(theme_dir, exist_ok=True)
        
        # Save the idea
        filepath = os.path.join(theme_dir, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(idea, f, indent=2)
            
            logger.info(f"Saved content idea to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving content idea: {str(e)}")
            raise ContentError(f"Failed to save content idea: {str(e)}") from e