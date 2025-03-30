"""
Main entry point for YouTube Shorts Automation System.
Initializes the application, loads configuration, and starts the GUI.
"""
import sys
import os
import logging
import argparse
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils.logging_setup import setup_logging
from utils.config_loader import ConfigLoader
from core.scheduler import WorkflowScheduler
from core.workflow_orchestrator import WorkflowOrchestrator

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation System")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no GUI)")
    parser.add_argument("--theme", type=str, help="Content theme to use in headless mode")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit (for headless mode)")
    return parser.parse_args()

def main():
    """Application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    log_dir = "logs"
    logger = setup_logging(log_dir=log_dir, debug=args.debug)
    logger.info("Starting YouTube Shorts Automation System")
    
    # Load configuration
    config_path = args.config if args.config else "config/config.yaml"
    config_loader = ConfigLoader(os.path.dirname(config_path))
    config_data = config_loader.load_config(os.path.basename(config_path))
    api_keys = config_loader.load_api_keys()
    
    logger.info(f"Loaded configuration from {config_path}")
    
    # Initialize background scheduler
    scheduler = WorkflowScheduler()
    
    # Run in headless mode if requested
    if args.headless:
        logger.info("Running in headless mode")
        
        # Create workflow orchestrator
        orchestrator = WorkflowOrchestrator.create_factory_instance(config_loader)
        
        # Run once if requested
        if args.run_once:
            logger.info("Executing single workflow run")
            try:
                results = orchestrator.execute_workflow(
                    theme=args.theme,
                    upload=True,
                    cleanup=True
                )
                
                logger.info(f"Workflow execution completed with status: {results['status']}")
                if results['status'] == 'completed':
                    sys.exit(0)
                else:
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Workflow execution failed: {str(e)}")
                sys.exit(1)
        else:
            # Schedule recurring workflow
            interval = config_loader.get_config_value("workflow.default_interval_minutes", 60)
            
            logger.info(f"Scheduling recurring workflow every {interval} minutes")
            
            def workflow_func():
                try:
                    results = orchestrator.execute_workflow(
                        theme=args.theme,
                        upload=True,
                        cleanup=True
                    )
                    logger.info(f"Workflow execution completed with status: {results['status']}")
                    return results
                except Exception as e:
                    logger.error(f"Workflow execution failed: {str(e)}")
                    return {"status": "failed", "error": str(e)}
            
            scheduler.schedule_workflow(
                workflow_id="headless_workflow",
                workflow_func=workflow_func,
                interval_minutes=interval
            )
            
            # Keep the application running
            try:
                logger.info("Press Ctrl+C to exit")
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt detected, shutting down")
                scheduler.shutdown()
                sys.exit(0)
    else:
        # Initialize GUI application
        app = QApplication(sys.argv)
        app.setApplicationName("YouTube Shorts Automation")
        
        # Initialize and show main window
        main_window = MainWindow(scheduler, config_loader)
        main_window.show()
        
        # Run the application
        result = app.exec_()
        
        # Shutdown scheduler before exiting
        scheduler.shutdown()
        
        logger.info("Application closed")
        sys.exit(result)

if __name__ == "__main__":
    main()