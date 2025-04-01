"""
Control panel UI component for YouTube Shorts Automation System.
Provides controls for starting, stopping, and configuring workflows.
"""
import logging
import sys
import time  # Added import for time module
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QPushButton, QLabel, QComboBox, QSpinBox, 
                            QCheckBox, QGroupBox, QLineEdit, QSlider,
                            QProgressBar, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from core.scheduler import WorkflowScheduler
from core.workflow_orchestrator import WorkflowOrchestrator
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class ControlPanel(QWidget):
    """
    Control panel UI component for managing workflow execution.
    """
    
    # Define signals
    workflow_started = pyqtSignal(str)  # Emits workflow ID
    workflow_stopped = pyqtSignal(str)  # Emits workflow ID
    workflow_error = pyqtSignal(str, str)  # Emits workflow ID and error message
    config_changed = pyqtSignal()  # Emits when configuration changes
    
    def __init__(self, scheduler: WorkflowScheduler, config_loader: ConfigLoader, parent=None):
        """
        Initialize the control panel.
        
        Args:
            scheduler: WorkflowScheduler instance
            config_loader: ConfigLoader instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.scheduler = scheduler
        self.config = config_loader
        
        # Store workflow details
        self.active_workflow_id = None
        self.workflow_status = {}
        
        # Set up the UI
        self._init_ui()
        
        # Set up timer for status updates
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
        
        logger.info("Control panel initialized")
    
    def _init_ui(self):
        """Initialize the user interface elements."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Add status section
        status_group = QGroupBox("Status")
        status_layout = QGridLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(QLabel("Current Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        status_layout.addWidget(QLabel("Progress:"), 1, 0)
        status_layout.addWidget(self.progress_bar, 1, 1)
        
        self.next_run_label = QLabel("Not scheduled")
        status_layout.addWidget(QLabel("Next Run:"), 2, 0)
        status_layout.addWidget(self.next_run_label, 2, 1)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Add control section
        control_group = QGroupBox("Workflow Control")
        control_layout = QGridLayout()
        
        # Interval settings
        control_layout.addWidget(QLabel("Run Interval (minutes):"), 0, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 1440)  # 1 minute to 24 hours
        self.interval_spin.setValue(1440)  # Default to 1 hour
        control_layout.addWidget(self.interval_spin, 0, 1)
        
        # Content theme
        control_layout.addWidget(QLabel("Content Theme:"), 1, 0)
        self.theme_combo = QComboBox()
        default_themes = self.config.get_config_value("content.default_themes", ["general"])
        self.theme_combo.addItem("nature")
        for theme in default_themes:
            self.theme_combo.addItem(theme)
        control_layout.addWidget(self.theme_combo, 1, 1)
        
        # Upload options
        control_layout.addWidget(QLabel("Upload Options:"), 2, 0)
        self.upload_check = QCheckBox("Upload to YouTube")
        self.upload_check.setChecked(False)
        control_layout.addWidget(self.upload_check, 2, 1)
        
        # Cleanup options
        control_layout.addWidget(QLabel("Cleanup:"), 3, 0)
        self.cleanup_check = QCheckBox("Clean up files after completion")
        self.cleanup_check.setChecked(False)
        control_layout.addWidget(self.cleanup_check, 3, 1)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Add button group
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Workflow")
        self.start_button.clicked.connect(self.start_workflow)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Workflow")
        self.stop_button.clicked.connect(self.stop_workflow)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.emergency_button = QPushButton("Emergency Stop")
        self.emergency_button.clicked.connect(self.emergency_stop)
        self.emergency_button.setStyleSheet("background-color: #f44336; color: white;")
        button_layout.addWidget(self.emergency_button)
        
        main_layout.addLayout(button_layout)
        
        # Add advanced settings button
        advanced_button = QPushButton("Advanced Settings...")
        advanced_button.clicked.connect(self._show_advanced_settings)
        main_layout.addWidget(advanced_button)
        
        # Set the main layout
        self.setLayout(main_layout)
    
    @pyqtSlot()
    def start_workflow(self):
        """Start a workflow execution."""
        try:
            # Get settings from UI
            interval_minutes = self.interval_spin.value()
            
            # Get theme
            theme = None if self.theme_combo.currentText() == "Random" else self.theme_combo.currentText()
            
            # Get upload and cleanup settings
            upload = self.upload_check.isChecked()
            cleanup = self.cleanup_check.isChecked()
            
            # Create a unique workflow ID
            workflow_id = f"workflow_{int(time.time())}"
            
            # Update UI
            self.status_label.setText("Starting...")
            self.progress_bar.setValue(0)
            
            # Create workflow orchestrator
            orchestrator = WorkflowOrchestrator.create_factory_instance(self.config)
            
            # Define the workflow function
            def workflow_func():
                try:
                    results = orchestrator.execute_workflow(
                        theme=theme,
                        upload=upload,
                        cleanup=cleanup
                    )
                    return results
                except Exception as e:
                    logger.error(f"Workflow execution error: {str(e)}")
                    # Emit error signal but don't re-raise to allow scheduler to continue
                    self.workflow_error.emit(workflow_id, str(e))
                    return {"status": "failed", "error": str(e)}
            
            # Schedule the workflow
            job = self.scheduler.schedule_workflow(
                workflow_id=workflow_id,
                workflow_func=workflow_func,
                interval_minutes=interval_minutes
            )
            
            # Update UI state
            self.active_workflow_id = workflow_id
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            # Store status
            self.workflow_status = {
                "id": workflow_id,
                "status": "scheduled",
                "interval": interval_minutes,
                "theme": theme,
                "upload": upload,
                "cleanup": cleanup
            }
            
            # Emit signal
            self.workflow_started.emit(workflow_id)
            
            logger.info(f"Started workflow {workflow_id} with interval {interval_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start workflow: {str(e)}")
    
    @pyqtSlot()
    def stop_workflow(self):
        """Stop the currently running workflow."""
        if self.active_workflow_id:
            try:
                # Stop the workflow in the scheduler
                self.scheduler.remove_workflow(self.active_workflow_id)
                
                # Update UI
                self.status_label.setText("Stopped")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
                # Emit signal
                self.workflow_stopped.emit(self.active_workflow_id)
                
                # Clear active workflow
                workflow_id = self.active_workflow_id
                self.active_workflow_id = None
                
                logger.info(f"Stopped workflow {workflow_id}")
                
            except Exception as e:
                logger.error(f"Error stopping workflow: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to stop workflow: {str(e)}")
    
    @pyqtSlot()
    def emergency_stop(self):
        """Emergency stop all workflows and the scheduler."""
        try:
            # Confirm with the user
            confirm = QMessageBox.question(
                self, "Emergency Stop",
                "This will stop all running and scheduled workflows. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Pause the scheduler
                self.scheduler.pause_all()
                
                # Update UI
                self.status_label.setText("EMERGENCY STOP")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
                # Clear active workflow
                self.active_workflow_id = None
                
                logger.warning("Emergency stop activated - all workflows paused")
                
                # Show a message to the user
                QMessageBox.information(
                    self, "Emergency Stop",
                    "All workflows have been stopped. To resume normal operation, restart the application."
                )
        except Exception as e:
            logger.error(f"Error during emergency stop: {str(e)}")
            QMessageBox.critical(self, "Error", f"Emergency stop failed: {str(e)}")
    
    @pyqtSlot()
    def _update_status(self):
        """Update the status display."""
        if not self.active_workflow_id:
            return
        
        try:
            # Get job status from scheduler
            status_info = self.scheduler.get_job_status(self.active_workflow_id)
            all_jobs = self.scheduler.get_all_jobs_status()
            
            if self.active_workflow_id in all_jobs:
                job_info = all_jobs[self.active_workflow_id]
                
                # Update next run time
                if job_info.get("next_run"):
                    self.next_run_label.setText(job_info["next_run"])
                
                # Update status
                status = job_info.get("status", "unknown")
                
                if status == "running":
                    self.status_label.setText("Running")
                    self.status_label.setStyleSheet("color: blue; font-weight: bold;")
                    # Pulse the progress bar while running
                    if self.progress_bar.value() >= 100:
                        self.progress_bar.setValue(0)
                    else:
                        self.progress_bar.setValue(self.progress_bar.value() + 5)
                        
                elif status == "error":
                    self.status_label.setText("Error")
                    self.status_label.setStyleSheet("color: red; font-weight: bold;")
                    self.progress_bar.setValue(0)
                    
                elif status == "scheduled":
                    if self.status_label.text() == "Running":
                        # Was running but now finished
                        self.status_label.setText("Completed")
                        self.status_label.setStyleSheet("color: green; font-weight: bold;")
                        self.progress_bar.setValue(100)
                        
                        # Schedule reset of progress bar
                        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
                    else:
                        self.status_label.setText("Scheduled")
                        self.status_label.setStyleSheet("color: black; font-weight: bold;")
                
                elif status == "paused":
                    self.status_label.setText("Paused")
                    self.status_label.setStyleSheet("color: orange; font-weight: bold;")
                
                else:
                    self.status_label.setText(status.capitalize())
                    self.status_label.setStyleSheet("font-weight: bold;")
            else:
                # Workflow not found in scheduler
                self.status_label.setText("Not Found")
                self.next_run_label.setText("Not scheduled")
                self.active_workflow_id = None
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")
            self.status_label.setText("Error")
    
    def _show_advanced_settings(self):
        """Show the advanced settings dialog."""
        # This would be implemented as a separate dialog
        # For now, just show a message
        QMessageBox.information(
            self, "Advanced Settings",
            "Advanced settings dialog would be shown here.\n"
            "This would include configuration for:\n"
            "- API settings\n"
            "- Content sources\n"
            "- Video style options\n"
            "- YouTube channel settings"
        )
        
    def set_theme_options(self, themes):
        """
        Update the theme combo box with new options.
        
        Args:
            themes: List of theme strings
        """
        self.theme_combo.clear()
        self.theme_combo.addItem("Random")
        for theme in themes:
            self.theme_combo.addItem(theme)
    
    def get_status(self):
        """
        Get the current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        return self.workflow_status.copy()