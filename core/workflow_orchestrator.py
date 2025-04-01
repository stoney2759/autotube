"""
Workflow orchestrator for YouTube Shorts Automation System.
Coordinates the execution of the entire content generation pipeline.
"""
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import random

from utils.error_handling import WorkflowError, log_execution_time
from utils.file_management import FileManager
from utils.config_loader import ConfigLoader

from core.content_generator import ContentGenerator
from core.image_generator import ImageGenerator
from core.video_generator import VideoGenerator
from core.audio_generator import AudioGenerator
from core.renderer import VideoRenderer
from core.uploader import YouTubeUploader

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """
    Coordinates the execution of the entire content generation pipeline.
    """
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        file_manager: FileManager,
        content_generator: ContentGenerator,
        image_generator: ImageGenerator,
        video_generator: VideoGenerator,
        audio_generator: AudioGenerator,
        video_renderer: VideoRenderer,
        uploader: YouTubeUploader
    ):
        """
        Initialize the workflow orchestrator.
        
        Args:
            config_loader: Configuration loader instance
            file_manager: File manager instance
            content_generator: Content generator instance
            image_generator: Image generator instance
            video_generator: Video generator instance
            audio_generator: Audio generator instance
            video_renderer: Video renderer instance
            uploader: YouTube uploader instance
        """
        self.config = config_loader
        self.file_manager = file_manager
        self.content_generator = content_generator
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.audio_generator = audio_generator
        self.video_renderer = video_renderer
        self.uploader = uploader
        
        logger.info("Workflow orchestrator initialized")
    
    @log_execution_time(logger=logger)
    def execute_workflow(
        self,
        theme: Optional[str] = None,
        upload: bool = True,
        cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the complete workflow from content generation to upload.
        
        Args:
            theme: Optional theme for content generation
            upload: Whether to upload the video to YouTube
            cleanup: Whether to clean up intermediate files after completion
            
        Returns:
            Dictionary with workflow results
            
        Raises:
            WorkflowError: If workflow execution fails
        """
        workflow_id = f"workflow_{int(time.time())}"
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        # Create project directory for this run
        project_id, project_dir = self.file_manager.create_project_dir()
        logger.info(f"Created project directory: {project_dir}")
        
        results = {
            "workflow_id": workflow_id,
            "project_id": project_id,
            "project_dir": project_dir,
            "started_at": time.time(),
            "status": "started",
            "steps": {}
        }
        
        try:
            # Step 1: Generate content idea
            logger.info("Step 1: Generating content idea")
            try:
                start_time = time.time()
                idea = self.content_generator.get_content_idea(theme)
                idea_with_templates = self.content_generator.apply_templates(idea)
                
                # Save idea details to results
                results["steps"]["content_generation"] = {
                    "status": "completed",
                    "duration": time.time() - start_time,
                    "details": {
                        "title": idea_with_templates.get("title", ""),
                        "theme": idea.get("theme", ""),
                        "description": idea_with_templates.get("description", "")
                    }
                }
                
                logger.info(f"Generated content idea: {idea_with_templates.get('title', '')}")
            except Exception as e:
                logger.error(f"Error in content generation step: {str(e)}")
                results["steps"]["content_generation"] = {
                    "status": "failed",
                    "error": str(e)
                }
                raise WorkflowError(f"Content generation failed: {str(e)}") from e
            
            # Step 2: Generate images
            logger.info("Step 2: Generating images")
            try:
                start_time = time.time()
                
                # Generate specific prompts for each image
                image_count = self.config.get_config_value("image.count_per_video", 5)
                image_prompts = self.content_generator.generate_video_prompts(
                    idea_with_templates, 
                    num_images=image_count
                )
                
                # Generate the images
                negative_prompt = self.config.get_config_value(
                    "image.negative_prompt", 
                    "low quality, blurry, distorted, deformed, disfigured"
                )
                image_paths = self.image_generator.generate_images(
                    prompts=image_prompts,
                    project_id=project_id,
                    negative_prompt=negative_prompt
                )
                
                # Save image details to results
                results["steps"]["image_generation"] = {
                    "status": "completed",
                    "duration": time.time() - start_time,
                    "details": {
                        "count": len(image_paths),
                        "paths": image_paths
                    }
                }
                
                logger.info(f"Generated {len(image_paths)} images")
            except Exception as e:
                logger.error(f"Error in image generation step: {str(e)}")
                results["steps"]["image_generation"] = {
                    "status": "failed",
                    "error": str(e)
                }
                raise WorkflowError(f"Image generation failed: {str(e)}") from e
            
            # Step 3: Generate audio
            logger.info("Step 3: Generating audio")
            try:
                start_time = time.time()
                
                # Determine if we need a script for TTS
                use_tts = self.config.get_config_value("audio.use_tts", False)
                script = None
                
                if use_tts:
                    # Use the video description or title as a script
                    script = idea_with_templates.get("description", idea_with_templates.get("title", ""))
                
                # Generate the audio
                mood = idea.get("mood", "upbeat")  # Get mood from idea or use default
                audio_path = self.audio_generator.generate_complete_audio(
                    project_id=project_id,
                    script=script,
                    mood=mood,
                    duration=self.config.get_config_value("video.duration_seconds", 60)
                )
                
                # Save audio details to results
                results["steps"]["audio_generation"] = {
                    "status": "completed",
                    "duration": time.time() - start_time,
                    "details": {
                        "path": audio_path,
                        "script": script,
                        "mood": mood
                    }
                }
                
                logger.info(f"Generated audio: {os.path.basename(audio_path)}")
            except Exception as e:
                logger.error(f"Error in audio generation step: {str(e)}")
                results["steps"]["audio_generation"] = {
                    "status": "failed",
                    "error": str(e)
                }
                raise WorkflowError(f"Audio generation failed: {str(e)}") from e
            
            # Step 4: Generate base video
            logger.info("Step 4: Generating base video")
            try:
                start_time = time.time()
                
                # Determine video style
                video_style = self.config.get_config_value("video.style", "standard")
                video_path = os.path.join(project_dir, "video", f"base_video_{int(time.time())}.mp4")
                
                # Extract captions from idea if available
                captions = []
                if idea_with_templates.get("captions"):
                    captions = idea_with_templates.get("captions")
                
                # Generate the video
                if video_style == "ken_burns":
                    video_path = self.video_generator.create_video_with_ken_burns(
                        image_paths=image_paths,
                        output_path=video_path,
                        captions=captions
                    )
                else:
                    video_path = self.video_generator.create_video_from_images(
                        image_paths=image_paths,
                        output_path=video_path,
                        captions=None,
                        add_intro=False,
                        add_outro=False,
                        title=idea_with_templates.get("title")
                    )
                
                # Save video details to results
                results["steps"]["video_generation"] = {
                    "status": "completed",
                    "duration": time.time() - start_time,
                    "details": {
                        "path": video_path,
                        "style": video_style
                    }
                }
                
                logger.info(f"Generated base video: {os.path.basename(video_path)}")
            except Exception as e:
                logger.error(f"Error in video generation step: {str(e)}")
                results["steps"]["video_generation"] = {
                    "status": "failed",
                    "error": str(e)
                }
                raise WorkflowError(f"Video generation failed: {str(e)}") from e
            
            # Step 5: Render final video
            logger.info("Step 5: Rendering final video")
            try:
                start_time = time.time()
                
                # Set up captions for rendering if needed
                render_captions = []
                
                # Render the final video
                final_video_path = self.video_renderer.render_final_video(
                    project_id=project_id,
                    video_path=video_path,
                    audio_path=audio_path,
                    title=idea_with_templates.get("title"),
                    captions=render_captions,
                    add_watermark=self.config.get_config_value("video.add_watermark", True)
                )
                
                # Save rendering details to results
                results["steps"]["video_rendering"] = {
                    "status": "completed",
                    "duration": time.time() - start_time,
                    "details": {
                        "path": final_video_path
                    }
                }
                
                logger.info(f"Rendered final video: {os.path.basename(final_video_path)}")
                
                # Compress video if needed
                max_size_mb = self.config.get_config_value("youtube.max_size_mb", 100)
                actual_size_mb = os.path.getsize(final_video_path) / (1024 * 1024)
                
                if actual_size_mb > max_size_mb:
                    logger.info(f"Video size ({actual_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB). Compressing...")
                    compressed_path = os.path.join(
                        os.path.dirname(final_video_path),
                        f"compressed_{os.path.basename(final_video_path)}"
                    )
                    
                    final_video_path = self.video_renderer.compress_video(
                        video_path=final_video_path,
                        output_path=compressed_path,
                        target_size_mb=max_size_mb
                    )
                    
                    results["steps"]["video_rendering"]["details"]["compressed_path"] = final_video_path
                    logger.info(f"Compressed video: {os.path.basename(final_video_path)}")
            except Exception as e:
                logger.error(f"Error in video rendering step: {str(e)}")
                results["steps"]["video_rendering"] = {
                    "status": "failed",
                    "error": str(e)
                }
                raise WorkflowError(f"Video rendering failed: {str(e)}") from e
            
            # Step 6: Upload to YouTube (if enabled)
            if upload:
                logger.info("Step 6: Uploading to YouTube")
                try:
                    start_time = time.time()
                    
                    # Prepare upload metadata
                    title = idea_with_templates.get("title", f"Generated Video {int(time.time())}")
                    description = idea_with_templates.get("description", "Auto-generated video")
                    tags = idea_with_templates.get("keywords", ["shorts", idea.get("theme", "video")])
                    
                    # Make sure we have a list of tags
                    if isinstance(tags, str):
                        tags = [tag.strip() for tag in tags.split(",")]
                    
                    # Limit title length to YouTube's maximum (100 characters)
                    if len(title) > 100:
                        title = title[:97] + "..."
                    
                    # Upload the video
                    privacy_status = self.config.get_config_value("youtube.default_privacy", "private")
                    upload_response = self.uploader.upload_video(
                        video_path=final_video_path,
                        title=title,
                        description=description,
                        tags=tags,
                        privacy_status=privacy_status
                    )
                    
                    # Save upload tracking data
                    upload_metadata = {
                        "title": title,
                        "description": description,
                        "tags": tags,
                        "theme": idea.get("theme"),
                        "project_id": project_id
                    }
                    
                    tracking_path = self.uploader.save_upload_details(
                        project_id=project_id,
                        upload_response=upload_response,
                        metadata=upload_metadata
                    )
                    
                    # Update tracking spreadsheet
                    self.uploader.update_spreadsheet(upload_response, upload_metadata)
                    
                    # Save upload details to results
                    results["steps"]["youtube_upload"] = {
                        "status": "completed",
                        "duration": time.time() - start_time,
                        "details": {
                            "video_id": upload_response.get("video_id"),
                            "url": upload_response.get("url"),
                            "tracking_path": tracking_path
                        }
                    }
                    
                    logger.info(f"Uploaded video to YouTube: {upload_response.get('video_id')}")
                    
                    # Schedule privacy change if configured
                    if privacy_status == "private" and self.config.get_config_value("youtube.auto_publish", False):
                        delay_hours = self.config.get_config_value("youtube.publish_delay_hours", 24)
                        publish_time = int(time.time() + delay_hours * 3600)
                        
                        self.uploader.schedule_privacy_change(
                            video_id=upload_response.get("video_id"),
                            new_privacy="public",
                            scheduled_time=publish_time
                        )
                        
                        results["steps"]["youtube_upload"]["details"]["scheduled_publish"] = {
                            "time": publish_time,
                            "privacy": "public"
                        }
                        
                        logger.info(f"Scheduled privacy change to public in {delay_hours} hours")
                except Exception as e:
                    logger.error(f"Error in YouTube upload step: {str(e)}")
                    results["steps"]["youtube_upload"] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    # Continue workflow despite upload failure
            
            # Step 7: Cleanup (if enabled)
            if cleanup:
                logger.info("Step 7: Cleanup")
                try:
                    start_time = time.time()
                    
                    # Keep the final video but clean up intermediate files
                    keep_final = True
                    
                    # Only clean up if we've successfully uploaded or upload wasn't required
                    if (not upload) or results.get("steps", {}).get("youtube_upload", {}).get("status") == "completed":
                        self.file_manager.cleanup_project(project_id, keep_final_video=keep_final)
                        
                        # Save cleanup details to results
                        results["steps"]["cleanup"] = {
                            "status": "completed",
                            "duration": time.time() - start_time,
                            "details": {
                                "kept_final_video": keep_final
                            }
                        }
                        
                        logger.info("Cleaned up project files")
                    else:
                        logger.info("Skipping cleanup due to upload failure")
                        results["steps"]["cleanup"] = {
                            "status": "skipped",
                            "details": {
                                "reason": "Upload failed, keeping files for debugging"
                            }
                        }
                except Exception as e:
                    logger.error(f"Error in cleanup step: {str(e)}")
                    results["steps"]["cleanup"] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    # Continue workflow despite cleanup failure
            
            # Workflow completed successfully
            results["status"] = "completed"
            results["completed_at"] = time.time()
            results["duration"] = results["completed_at"] - results["started_at"]
            
            logger.info(f"Workflow completed successfully in {results['duration']:.2f} seconds")
            return results
            
        except Exception as e:
            # Record workflow failure
            results["status"] = "failed"
            results["error"] = str(e)
            results["completed_at"] = time.time()
            results["duration"] = results["completed_at"] - results["started_at"]
            
            logger.error(f"Workflow failed: {str(e)}")
            
            # Save failure metadata
            metadata_path = self.file_manager.save_project_metadata(project_id, results)
            logger.info(f"Saved failure metadata to: {metadata_path}")
            
            # Re-raise the exception
            raise WorkflowError(f"Workflow execution failed: {str(e)}") from e
        finally:
            # Save workflow results metadata regardless of success/failure
            metadata_path = self.file_manager.save_project_metadata(project_id, results)
            logger.info(f"Saved workflow metadata to: {metadata_path}")
    
    def create_factory_instance(config_loader: ConfigLoader) -> 'WorkflowOrchestrator':
        """
        Factory method to create a fully configured WorkflowOrchestrator instance.
        
        Args:
            config_loader: Configuration loader instance
            
        Returns:
            Configured WorkflowOrchestrator instance
        """
        # Create file manager
        file_manager = FileManager()
        
        # Create all the component instances
        content_generator = ContentGenerator(config_loader)
        image_generator = ImageGenerator(config_loader, file_manager)
        video_generator = VideoGenerator(config_loader, file_manager)
        audio_generator = AudioGenerator(config_loader, file_manager)
        video_renderer = VideoRenderer(config_loader, file_manager)
        uploader = YouTubeUploader(config_loader, file_manager)
        
        # Create and return the orchestrator
        return WorkflowOrchestrator(
            config_loader=config_loader,
            file_manager=file_manager,
            content_generator=content_generator,
            image_generator=image_generator,
            video_generator=video_generator,
            audio_generator=audio_generator,
            video_renderer=video_renderer,
            uploader=uploader
        )