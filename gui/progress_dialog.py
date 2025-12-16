"""Progress dialog for transcription operations."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtCore import Qt

from core.logging_config import get_logger

logger = get_logger(__name__)


class ProgressDialog(QDialog):
    """Dialog showing transcription progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcribing...")
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
    
    def update_progress(self, progress: float, message: str) -> None:
        """Update progress bar and message.
        
        Args:
            progress: Progress value (0.0-1.0)
            message: Status message
        """
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(message)
    
    def set_message(self, message: str) -> None:
        """Set status message."""
        self.status_label.setText(message)

