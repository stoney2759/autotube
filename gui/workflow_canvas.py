"""
Workflow visualization canvas for YouTube Shorts Automation System.
Provides a visual representation of the workflow nodes and connections.
"""
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
                            QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont

logger = logging.getLogger(__name__)

class WorkflowCanvas(QWidget):
    """
    Visual canvas for displaying workflow nodes and their connections.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the workflow canvas.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set up the UI
        self._init_ui()
        
        # Define the workflow nodes
        self.node_items = {}
        self.node_text_items = {}
        self.node_status = {}
        
        # Create the initial workflow visualization
        self._create_workflow_nodes()
        
        logger.info("Workflow canvas initialized")
    
    def _init_ui(self):
        """Initialize the user interface elements."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create graphics scene and view
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Add view to layout
        layout.addWidget(self.view)
        
        # Set the layout
        self.setLayout(layout)
    
    def _create_workflow_nodes(self):
        """Create the workflow nodes and connections in the scene."""
        # Define node positions and properties
        nodes = [
            {"id": "idea_gen", "name": "Idea Generator", "x": 50, "y": 50, "color": "#4CAF50"},
            {"id": "prompt_gen", "name": "Prompt Creator", "x": 200, "y": 50, "color": "#2196F3"},
            {"id": "image_gen", "name": "Image Generator", "x": 350, "y": 50, "color": "#9C27B0"},
            {"id": "audio_gen", "name": "Audio Generator", "x": 350, "y": 150, "color": "#9C27B0"},
            {"id": "video_render", "name": "Video Renderer", "x": 500, "y": 100, "color": "#FF9800"},
            {"id": "uploader", "name": "YouTube Uploader", "x": 650, "y": 100, "color": "#F44336"}
        ]
        
        # Create nodes
        for node in nodes:
            # Create the node rectangle
            node_item = QGraphicsRectItem(0, 0, 120, 60)
            node_item.setPos(node["x"], node["y"])
            node_item.setBrush(QBrush(QColor(node["color"])))
            node_item.setPen(QPen(Qt.white, 2))
            node_item.setData(0, node["id"])
            self.scene.addItem(node_item)
            
            # Create the node text
            text_item = QGraphicsTextItem(node["name"])
            text_item.setDefaultTextColor(Qt.white)
            text_item.setFont(QFont("Arial", 10, QFont.Bold))
            
            # Center the text in the node
            text_rect = text_item.boundingRect()
            text_x = node["x"] + (120 - text_rect.width()) / 2
            text_y = node["y"] + (60 - text_rect.height()) / 2
            text_item.setPos(text_x, text_y)
            
            self.scene.addItem(text_item)
            
            # Store references to the items
            self.node_items[node["id"]] = node_item
            self.node_text_items[node["id"]] = text_item
            self.node_status[node["id"]] = "waiting"
        
        # Define connections between nodes
        connections = [
            {"from": "idea_gen", "to": "prompt_gen"},
            {"from": "prompt_gen", "to": "image_gen"},
            {"from": "prompt_gen", "to": "audio_gen"},
            {"from": "image_gen", "to": "video_render"},
            {"from": "audio_gen", "to": "video_render"},
            {"from": "video_render", "to": "uploader"}
        ]
        
        # Create connections
        for conn in connections:
            from_node = self.node_items[conn["from"]]
            to_node = self.node_items[conn["to"]]
            
            # Calculate connection points
            from_center = from_node.pos() + QPointF(from_node.rect().width() / 2, from_node.rect().height() / 2)
            to_center = to_node.pos() + QPointF(to_node.rect().width() / 2, to_node.rect().height() / 2)
            
            # Create the connection line
            line = QGraphicsLineItem(from_center.x(), from_center.y(), to_center.x(), to_center.y())
            line.setPen(QPen(Qt.lightGray, 2, Qt.DashLine))
            self.scene.addItem(line)
    
    def update_node_status(self, node_id: str, status: str) -> None:
        """
        Update the status of a workflow node.
        
        Args:
            node_id: ID of the node to update
            status: New status (active, completed, waiting, error)
        """
        if node_id not in self.node_items:
            logger.warning(f"Attempted to update unknown node: {node_id}")
            return
        
        # Define status colors
        status_colors = {
            "active": "#2196F3",     # Blue
            "completed": "#4CAF50",  # Green
            "waiting": "#9E9E9E",    # Gray
            "error": "#F44336"       # Red
        }
        
        if status in status_colors:
            # Update the node appearance
            node_item = self.node_items[node_id]
            node_item.setBrush(QBrush(QColor(status_colors[status])))
            
            # Update stored status
            self.node_status[node_id] = status
            
            logger.debug(f"Updated node {node_id} status to {status}")
    
    def reset_all_nodes(self) -> None:
        """Reset all nodes to their default state."""
        for node_id, node in self.node_items.items():
            # Get the original color from node definition
            original_color = "#9E9E9E"  # Default gray
            
            # Find node definition to get original color
            nodes = [
                {"id": "idea_gen", "color": "#4CAF50"},
                {"id": "prompt_gen", "color": "#2196F3"},
                {"id": "image_gen", "color": "#9C27B0"},
                {"id": "audio_gen", "color": "#9C27B0"},
                {"id": "video_render", "color": "#FF9800"},
                {"id": "uploader", "color": "#F44336"}
            ]
            
            for node_def in nodes:
                if node_def["id"] == node_id:
                    original_color = node_def["color"]
                    break
            
            # Reset the node appearance
            node.setBrush(QBrush(QColor(original_color)))
            
            # Update stored status
            self.node_status[node_id] = "waiting"
        
        logger.debug("Reset all nodes to default state")
    
    def refresh(self) -> None:
        """Refresh the workflow visualization."""
        # Clear the scene
        self.scene.clear()
        self.node_items.clear()
        self.node_text_items.clear()
        
        # Recreate the nodes
        self._create_workflow_nodes()
        
        logger.debug("Refreshed workflow visualization")