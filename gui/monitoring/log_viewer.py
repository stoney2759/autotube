"""
Log viewer component for YouTube Shorts Automation System.
Displays and filters log messages.
"""
import os
import logging
import time
import weakref
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QComboBox, QLabel, QCheckBox,
                            QFileDialog, QSpinBox, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

logger = logging.getLogger(__name__)

class LogViewer(QWidget):
    """
    Log viewer component for displaying and filtering log messages.
    """
    
    class QtHandler(logging.Handler, QObject):
        """Custom logging handler that emits signals with log records."""
        
        log_record_signal = pyqtSignal(object)
        
        def __init__(self):
            logging.Handler.__init__(self)
            QObject.__init__(self)
            self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
        
        def emit(self, record):
            self.log_record_signal.emit(record)
    
    def __init__(self, parent=None):
        """
        Initialize the log viewer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set up the UI
        self._init_ui()
        
        # Set up the custom log handler
        self.log_handler = self.QtHandler()
        self.log_handler.log_record_signal.connect(self._handle_log_record)
        self.log_handler.setLevel(logging.INFO)  # Default to INFO level
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        
        # Auto-scroll timer
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self._auto_scroll)
        self.auto_scroll_timer.start(100)  # Check every 100ms
        
        # Keep weak reference to timer
        self._timer_ref = weakref.ref(self.auto_scroll_timer)
        
        logger.info("Log viewer initialized")
    
    def _init_ui(self):
        """Initialize the user interface elements."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Add controls
        controls_layout = QHBoxLayout()
        
        # Log level filter
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self._set_log_level)
        controls_layout.addWidget(QLabel("Level:"))
        controls_layout.addWidget(self.level_combo)
        
        # Module filter
        self.module_filter = QComboBox()
        self.module_filter.addItem("All Modules")
        self.module_filter.currentTextChanged.connect(self._filter_logs)
        controls_layout.addWidget(QLabel("Module:"))
        controls_layout.addWidget(self.module_filter)
        
        # Search filter
        self.search_check = QCheckBox("Search:")
        self.search_check.stateChanged.connect(self._filter_logs)
        controls_layout.addWidget(self.search_check)
        
        self.search_text = QLineEdit()
        self.search_text.setEnabled(False)
        self.search_text.textChanged.connect(self._filter_logs)
        self.search_check.stateChanged.connect(self.search_text.setEnabled)
        controls_layout.addWidget(self.search_text)
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)
        
        # Max lines
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(100, 10000)
        self.max_lines_spin.setValue(1000)
        self.max_lines_spin.setSingleStep(100)
        controls_layout.addWidget(QLabel("Max Lines:"))
        controls_layout.addWidget(self.max_lines_spin)
        
        # Clear and save buttons
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_logs)
        controls_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("Save Logs...")
        self.save_button.clicked.connect(self._save_logs)
        controls_layout.addWidget(self.save_button)
        
        main_layout.addLayout(controls_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_text)
        
        # Store log records for filtering
        self.log_records = []
        self.modules = set()
        
        # Set the layout
        self.setLayout(main_layout)
    
    @pyqtSlot(object)
    def _handle_log_record(self, record):
        """
        Handle a log record emitted by the custom handler.
        
        Args:
            record: Log record object
        """
        # Store the record
        self.log_records.append(record)
        
        # Keep track of modules
        module = record.name
        if module not in self.modules:
            self.modules.add(module)
            self.module_filter.addItem(module)
        
        # Apply filters
        if self._should_display_record(record):
            self._append_record_to_text(record)
        
        # Limit the number of stored records
        max_records = self.max_lines_spin.value()
        if len(self.log_records) > max_records:
            self.log_records = self.log_records[-max_records:]
    
    def _should_display_record(self, record):
        """
        Check if a log record should be displayed based on current filters.
        
        Args:
            record: Log record object
            
        Returns:
            True if the record should be displayed, False otherwise
        """
        # Check level filter
        level_name = self.level_combo.currentText()
        if record.levelno < logging._nameToLevel[level_name]:
            return False
        
        # Check module filter
        if self.module_filter.currentText() != "All Modules" and record.name != self.module_filter.currentText():
            return False
        
        # Check search filter
        if self.search_check.isChecked() and self.search_text.text():
            search_term = self.search_text.text().lower()
            message = self.log_handler.format(record).lower()
            if search_term not in message:
                return False
        
        return True
    
    def _append_record_to_text(self, record):
        """
        Append a formatted log record to the text area.
        
        Args:
            record: Log record object
        """
        # Set text color based on level
        text_format = QTextCharFormat()
        
        if record.levelno >= logging.CRITICAL:
            text_format.setForeground(QColor("purple"))
        elif record.levelno >= logging.ERROR:
            text_format.setForeground(QColor("red"))
        elif record.levelno >= logging.WARNING:
            text_format.setForeground(QColor("orange"))
        elif record.levelno >= logging.INFO:
            text_format.setForeground(QColor("blue"))
        else:  # DEBUG
            text_format.setForeground(QColor("gray"))
        
        # Format the record
        formatted_text = self.log_handler.format(record)
        
        # Append to text area
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.setCharFormat(text_format)
        cursor.insertText(formatted_text + "\n")
        
        # Limit the number of lines in the text area
        self._trim_log_text()
    
    def _trim_log_text(self):
        """Trim the log text area to the maximum number of lines."""
        max_lines = self.max_lines_spin.value()
        document = self.log_text.document()
        
        if document.lineCount() > max_lines:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                               document.lineCount() - max_lines)
            cursor.removeSelectedText()
    
    def _auto_scroll(self):
        """Auto-scroll the log text area to the bottom."""
        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    @pyqtSlot(str)
    def _set_log_level(self, level_name):
        """
        Set the log level for the handler.
        
        Args:
            level_name: Name of the log level
        """
        level = logging._nameToLevel[level_name]
        self.log_handler.setLevel(level)
        self._filter_logs()
    
    @pyqtSlot()
    def _filter_logs(self):
        """Apply filters and refresh the log text display."""
        # Clear the text area
        self.log_text.clear()
        
        # Apply filters to stored records
        for record in self.log_records:
            if self._should_display_record(record):
                self._append_record_to_text(record)
    
    @pyqtSlot()
    def _clear_logs(self):
        """Clear the log text area and stored records."""
        self.log_text.clear()
        self.log_records.clear()
    
    @pyqtSlot()
    def _save_logs(self):
        """Save the current log content to a file."""
        try:
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"logs/log_export_{timestamp}.txt"
            
            # Get save file name
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Logs", default_filename, "Text Files (*.txt);;All Files (*)")
            
            if not filename:
                return
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Save logs
            with open(filename, 'w') as f:
                f.write(self.log_text.toPlainText())
            
            logger.info(f"Logs saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving logs: {str(e)}")
    
    def add_log_message(self, message, level=logging.INFO):
        """
        Add a custom log message to the viewer.
        
        Args:
            message: Message text
            level: Logging level
        """
        logger.log(level, message)
    
    def cleanup(self):
        """Clean up resources before object destruction."""
        try:
            # Stop the timer
            timer = self._timer_ref()
            if timer and timer.isActive():
                timer.stop()
            
            # Remove handler from loggers
            root_logger = logging.getLogger()
            if self.log_handler in root_logger.handlers:
                root_logger.removeHandler(self.log_handler)
            
            # Disconnect signals
            try:
                self.log_handler.log_record_signal.disconnect()
            except Exception:
                pass
        except Exception:
            # Swallow exceptions during cleanup
            pass
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event)