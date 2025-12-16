"""Settings dialog for configuration."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QGroupBox, QMessageBox, QCheckBox
)

from config.manager import config_manager
from core.logging_config import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Dialog for application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_layout = QVBoxLayout()
        
        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.addWidget(QLabel("FFmpeg Path:"))
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("Path to ffmpeg.exe")
        ffmpeg_row.addWidget(self.ffmpeg_path_edit)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_ffmpeg)
        ffmpeg_row.addWidget(browse_button)
        
        ffmpeg_layout.addLayout(ffmpeg_row)
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["txt", "srt", "vtt", "json"])
        format_row.addWidget(self.format_combo)
        output_layout.addLayout(format_row)
        
        # Timestamp option (only for TXT format)
        self.include_timestamps_checkbox = QCheckBox("Include timestamps in TXT output (e.g., 00:30)")
        output_layout.addWidget(self.include_timestamps_checkbox)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        language_group = QGroupBox("Language")
        language_layout = QVBoxLayout()
        
        input_lang_row = QHBoxLayout()
        input_lang_row.addWidget(QLabel("Input Language:"))
        self.input_lang_combo = QComboBox()
        self.input_lang_combo.addItems(["auto", "en", "de", "fr", "es", "it", "pt", "ru", "zh", "ja"])
        input_lang_row.addWidget(self.input_lang_combo)
        language_layout.addLayout(input_lang_row)
        
        language_group.setLayout(language_layout)
        layout.addWidget(language_group)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load current settings."""
        ffmpeg_path = config_manager.get_value("ffmpeg_path", "")
        self.ffmpeg_path_edit.setText(ffmpeg_path)
        
        output_format = config_manager.get_value("output.format", "txt")
        index = self.format_combo.findText(output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        
        include_timestamps = config_manager.get_value("output.include_timestamps", True)
        self.include_timestamps_checkbox.setChecked(include_timestamps)
        
        input_lang = config_manager.get_value("languages.input", "auto")
        index = self.input_lang_combo.findText(input_lang)
        if index >= 0:
            self.input_lang_combo.setCurrentIndex(index)
    
    def _browse_ffmpeg(self) -> None:
        """Browse for FFmpeg executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select FFmpeg Executable",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.ffmpeg_path_edit.setText(file_path)
    
    def _save_settings(self) -> None:
        """Save settings."""
        try:
            ffmpeg_path = self.ffmpeg_path_edit.text().strip()
            if ffmpeg_path:
                if not Path(ffmpeg_path).exists():
                    QMessageBox.warning(self, "Error", "FFmpeg path does not exist")
                    return
                config_manager.set_value("ffmpeg_path", ffmpeg_path)
            
            config_manager.set_value("output.format", self.format_combo.currentText())
            config_manager.set_value("output.include_timestamps", self.include_timestamps_checkbox.isChecked())
            config_manager.set_value("languages.input", self.input_lang_combo.currentText())
            
            QMessageBox.information(self, "Success", "Settings saved successfully")
            self.accept()
        except Exception as e:
            logger.exception("Failed to save settings")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

