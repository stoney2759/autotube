"""
Main window for YouTube Shorts Automation System GUI.
"""
import logging
import os
import sys
import time
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
                            QMenuBar, QAction, QToolBar, QStatusBar, 
                            QMessageBox, QFileDialog, QDialog, QLabel, 
                            QLineEdit, QPushButton, QGridLayout, QFormLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont

from gui.workflow_canvas import WorkflowCanvas
from gui.control_panel import ControlPanel
from gui.monitoring.log_viewer import LogViewer
from core.scheduler import WorkflowScheduler
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Main application window for YouTube Shorts Automation System.
    """
    
    def __init__(self, scheduler: WorkflowScheduler, config_loader: ConfigLoader, parent=None):
        """
        Initialize the main window.
        
        Args:
            scheduler: WorkflowScheduler instance
            config_loader: ConfigLoader instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.scheduler = scheduler
        self.config = config_loader
        
        # Set window properties
        self.setWindowTitle("AutoTube Beta 0.2")
        self.setMinimumSize(1200, 800)
        
        # Create main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create workflow visualization
        self.workflow_canvas = WorkflowCanvas()
        
        # Create control panel
        self.control_panel = ControlPanel(self.scheduler, self.config)
        
        # Connect control panel signals
        self.control_panel.workflow_started.connect(self._on_workflow_started)
        self.control_panel.workflow_stopped.connect(self._on_workflow_stopped)
        self.control_panel.workflow_error.connect(self._on_workflow_error)
        
        # Create log viewer
        self.log_viewer = LogViewer()
        
        # Create tab widget for different sections
        self.tabs = QTabWidget()
        self.tabs.addTab(self.workflow_canvas, "Workflow")
        
        # Add components to layout
        self.layout.addWidget(self.control_panel)
        self.layout.addWidget(self.tabs, 3)  # Workflow takes more space
        self.layout.addWidget(self.log_viewer, 1)  # Log viewer takes less space
        
        # Set up status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Setup menu and toolbar
        self._create_menu()
        self._create_toolbar()
        
        logger.info("Main window initialized")
    
    def _create_menu(self):
        """Create application menu"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        new_action = QAction("&New Workflow", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_workflow)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Workflow", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_workflow)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Workflow", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_workflow)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        
        preferences_action = QAction("&Preferences", self)
        preferences_action.triggered.connect(self._show_preferences)
        edit_menu.addAction(preferences_action)
        
        api_keys_action = QAction("&API Keys", self)
        api_keys_action.triggered.connect(self._show_api_keys)
        edit_menu.addAction(api_keys_action)
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_view)
        view_menu.addAction(refresh_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        run_once_action = QAction("&Run Once", self)
        run_once_action.triggered.connect(self._run_workflow_once)
        tools_menu.addAction(run_once_action)
        
        monitor_action = QAction("&Monitor Uploads", self)
        monitor_action.triggered.connect(self._show_monitor)
        tools_menu.addAction(monitor_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self._show_docs)
        help_menu.addAction(docs_action)
    
    def _create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        start_action = QAction("Start", self)
        start_action.triggered.connect(self.control_panel.start_workflow)
        toolbar.addAction(start_action)
        
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.control_panel.stop_workflow)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_preferences)
        toolbar.addAction(settings_action)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Are you sure you want to exit? Any running workflows will be stopped.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Stop the scheduler
            self.scheduler.shutdown()
            logger.info("Application closing")
            event.accept()
        else:
            event.ignore()
    
    def _new_workflow(self):
        """Create a new workflow configuration"""
        logger.info("New workflow requested")
        QMessageBox.information(
            self, "New Workflow",
            "This would create a new workflow configuration.\n"
            "Feature not fully implemented yet."
        )
    
    def _open_workflow(self):
        """Open an existing workflow configuration"""
        logger.info("Open workflow requested")
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Workflow Configuration",
            "config/workflow_templates",
            "YAML Files (*.yaml);;All Files (*)"
        )
        
        if filename:
            QMessageBox.information(
                self, "Open Workflow",
                f"Selected file: {filename}\n"
                "Feature not fully implemented yet."
            )
    
    def _save_workflow(self):
        """Save the current workflow configuration"""
        logger.info("Save workflow requested")
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Workflow Configuration",
            "config/workflow_templates/workflow_config.yaml",
            "YAML Files (*.yaml);;All Files (*)"
        )
        
        if filename:
            QMessageBox.information(
                self, "Save Workflow",
                f"Would save to: {filename}\n"
                "Feature not fully implemented yet."
            )
    
    def _show_preferences(self):
        """Show the preferences dialog"""
        logger.info("Preferences requested")
        
        QMessageBox.information(
            self, "Preferences",
            "This would show the application preferences dialog.\n"
            "Feature not fully implemented yet."
        )
    
    def _show_api_keys(self):
        """Show the API keys configuration dialog"""
        logger.info("API keys configuration requested")
        
        QMessageBox.information(
            self, "API Keys",
            "This would show the API keys configuration dialog.\n"
            "Feature not fully implemented yet.\n\n"
            "For now, edit the config/api_keys.yaml file directly."
        )
    
    def _refresh_view(self):
        """Refresh the workflow view"""
        logger.info("View refresh requested")
        self.workflow_canvas.refresh()
        self.status_bar.showMessage("View refreshed", 3000)
    
    def _run_workflow_once(self):
        """Run the workflow once without scheduling"""
        logger.info("Run once requested")
        
        # Get settings from control panel
        settings = self.control_panel.get_status()
        theme = settings.get("theme")
        upload = settings.get("upload", True)
        cleanup = settings.get("cleanup", True)
        
        # Generate a unique workflow ID
        workflow_id = f"single_run_{int(time.time())}"
        
        # Update status
        self.status_bar.showMessage("Running single workflow...", 0)
        
        # Create orchestrator and execute
        try:
            from core.workflow_orchestrator import WorkflowOrchestrator
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
                    return {"status": "failed", "error": str(e)}
            
            # Schedule a one-time workflow
            self.scheduler.schedule_one_time_workflow(
                workflow_id=workflow_id,
                workflow_func=workflow_func
            )
            
            self.status_bar.showMessage("Single workflow scheduled", 3000)
            
        except Exception as e:
            logger.error(f"Error scheduling single workflow: {str(e)}")
            self.status_bar.showMessage(f"Error: {str(e)}", 5000)
            QMessageBox.critical(
                self, "Error",
                f"Failed to schedule workflow: {str(e)}"
            )
    
    def _show_monitor(self):
        """Show the upload monitor"""
        logger.info("Upload monitor requested")
        
        QMessageBox.information(
            self, "Upload Monitor",
            "This would show the YouTube upload monitor.\n"
            "Feature not fully implemented yet."
        )
    
    def _show_about(self):
        """Show the about dialog"""
        QMessageBox.about(
            self,
            "About YouTube Shorts Automation",
            "<h1>AutoTube</h1>"
            "<p>Version 0.0.2</p>"
            "<p>A fully automated system for generating and uploading YouTube Shorts content.</p>"
            "<p>This application automates the entire content creation pipeline:</p>"
            "<ul>"
            "<li>Generating ideas</li>"
            "<li>Creating images</li>"
            "<li>Producing videos</li>"
            "<li>Adding audio</li>"
            "<li>Uploading to YouTube</li>"
            "</ul>"
        )
    
    def _show_docs(self):
        """Show the documentation"""
        QMessageBox.information(
            self, "Documentation",
            "Documentation would open in a browser.\n"
            "Feature not fully implemented yet."
        )
    
    def _on_workflow_started(self, workflow_id):
        """Handle workflow started signal"""
        self.status_bar.showMessage(f"Workflow {workflow_id} started", 5000)
        self.workflow_canvas.update_node_status("idea_gen", "active")
    
    def _on_workflow_stopped(self, workflow_id):
        """Handle workflow stopped signal"""
        self.status_bar.showMessage(f"Workflow {workflow_id} stopped", 5000)
        self.workflow_canvas.reset_all_nodes()
    
    def _on_workflow_error(self, workflow_id, error_message):
        """Handle workflow error signal"""
        self.status_bar.showMessage(f"Workflow error: {error_message}", 5000)
        self.workflow_canvas.update_node_status("video_render", "error")
        
        # Log the error
        self.log_viewer.add_log_message(f"Workflow {workflow_id} error: {error_message}", logging.ERROR)
        
        # Show error dialog
        QMessageBox.critical(
            self, "Workflow Error",
            f"An error occurred in workflow {workflow_id}:\n\n{error_message}"
        )