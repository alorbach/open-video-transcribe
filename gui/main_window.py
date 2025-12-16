"""Main window for Open Video Transcribe."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QComboBox, QHBoxLayout, QGroupBox
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from core.controller import Controller
from core.logging_config import get_logger
from config.manager import config_manager
from gui.progress_dialog import ProgressDialog
from gui.settings_dialog import SettingsDialog

logger = get_logger(__name__)

WHISPER_MODELS = [
    "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    "medium", "medium.en", "large-v1", "large-v2", "large-v3",
    "distil-small.en", "distil-medium.en", "distil-large-v2", "distil-large-v3"
]

WHISPER_LANGUAGES = [
    ("auto", "Auto-detect"),
    ("en", "English"), ("de", "German"), ("fr", "French"), ("es", "Spanish"),
    ("it", "Italian"), ("pt", "Portuguese"), ("ru", "Russian"), ("zh", "Chinese"),
    ("ja", "Japanese"), ("ko", "Korean"), ("ar", "Arabic"), ("hi", "Hindi"),
    ("nl", "Dutch"), ("pl", "Polish"), ("tr", "Turkish"), ("sv", "Swedish"),
    ("cs", "Czech"), ("hu", "Hungarian"), ("fi", "Finnish"), ("ro", "Romanian")
]


class MainWindow(QWidget):
    """Main application window."""
    
    def __init__(self, cuda_available: bool = False):
        super().__init__()
        
        self.controller = Controller()
        self.cuda_available = cuda_available
        self.progress_dialog: ProgressDialog = None
        
        self.setWindowTitle("Open Video Transcribe")
        self.setFixedSize(500, 400)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = self.status_label.font()
        font.setPointSize(12)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        self.select_file_button = QPushButton("Select Video/Audio File")
        self.select_file_button.clicked.connect(self._select_file)
        layout.addWidget(self.select_file_button)
        
        model_group = QGroupBox("Model Settings")
        model_layout = QVBoxLayout()
        
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(WHISPER_MODELS)
        model_row.addWidget(self.model_combo)
        model_layout.addLayout(model_row)
        
        quant_row = QHBoxLayout()
        quant_row.addWidget(QLabel("Quantization:"))
        self.quant_combo = QComboBox()
        self.quant_combo.addItems(["float16", "float32", "int8"])
        quant_row.addWidget(self.quant_combo)
        model_layout.addLayout(quant_row)
        
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"] if cuda_available else ["cpu"])
        device_row.addWidget(self.device_combo)
        model_layout.addLayout(device_row)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        lang_group = QGroupBox("Language")
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Input Language:"))
        self.language_combo = QComboBox()
        for code, name in WHISPER_LANGUAGES:
            self.language_combo.addItem(name, code)
        lang_layout.addWidget(self.language_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        button_row = QHBoxLayout()
        self.load_model_button = QPushButton("Load Model")
        self.load_model_button.clicked.connect(self._load_model)
        button_row.addWidget(self.load_model_button)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._show_settings)
        button_row.addWidget(self.settings_button)
        
        layout.addLayout(button_row)
        
        self._connect_signals()
        self._load_config()
        
        logger.info("MainWindow initialized")
    
    def _connect_signals(self) -> None:
        """Connect controller signals."""
        self.controller.status_updated.connect(self._update_status)
        self.controller.progress_updated.connect(self._update_progress)
        self.controller.transcription_completed.connect(self._on_transcription_completed)
        self.controller.error_occurred.connect(self._show_error)
        self.controller.widgets_enabled.connect(self._set_widgets_enabled)
    
    def _load_config(self) -> None:
        """Load configuration."""
        model_name = self.controller.current_model_name or "large-v3"
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        quantization = config_manager.get_value("model.quantization", "float16")
        index = self.quant_combo.findText(quantization)
        if index >= 0:
            self.quant_combo.setCurrentIndex(index)
        
        device = config_manager.get_value("model.device", "cuda" if self.cuda_available else "cpu")
        index = self.device_combo.findText(device)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
        
        language = config_manager.get_value("languages.input", "auto")
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == language:
                self.language_combo.setCurrentIndex(i)
                break
    
    @Slot()
    def _select_file(self) -> None:
        """Select video or audio file for transcription."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video or Audio File",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.webm *.mov);;"
            "Audio Files (*.mp3 *.wav *.m4a *.flac);;"
            "All Files (*)"
        )
        
        if file_path:
            logger.info(f"Selected file: {file_path}")
            self._ask_transcription_mode(Path(file_path))
    
    def _ask_transcription_mode(self, file_path: Path) -> None:
        """Ask user if they want full transcription or test mode (5 minutes)."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Transcription Mode")
        msg_box.setText("Choose transcription mode:")
        msg_box.setInformativeText(
            "Full File: Transcribe the entire file\n"
            "Test Mode: Transcribe only first 5 minutes"
        )
        
        full_button = msg_box.addButton("Full File", QMessageBox.ButtonRole.AcceptRole)
        test_button = msg_box.addButton("Test Mode (5 min)", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.setDefaultButton(full_button)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_button:
            return
        elif clicked_button == test_button:
            logger.info("Starting transcription in test mode (5 minutes)")
            self.controller.transcribe_file(file_path, test_mode=True)
        else:
            logger.info("Starting full file transcription")
            self.controller.transcribe_file(file_path, test_mode=False)
    
    @Slot()
    def _load_model(self) -> None:
        """Load transcription model."""
        model_name = self.model_combo.currentText()
        quantization = self.quant_combo.currentText()
        device = self.device_combo.currentText()
        
        self.controller.load_model("whisper", model_name, quantization, device)
    
    @Slot()
    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            if self.controller.converter is None:
                ffmpeg_path = config_manager.get_value("ffmpeg_path", "")
                if ffmpeg_path:
                    try:
                        self.controller.set_ffmpeg_path(ffmpeg_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to set FFmpeg path: {e}")
            
            language_code = self.language_combo.currentData()
            self.controller.set_language(language_code)
    
    @Slot(str)
    def _update_status(self, status: str) -> None:
        """Update status label."""
        self.status_label.setText(status)
    
    @Slot(float, str)
    def _update_progress(self, progress: float, message: str) -> None:
        """Update progress."""
        if self.progress_dialog is None:
            self.progress_dialog = ProgressDialog(self)
            self.progress_dialog.show()
        
        self.progress_dialog.update_progress(progress, message)
    
    @Slot(str, Path)
    def _on_transcription_completed(self, text: str, output_path: Path) -> None:
        """Handle transcription completion."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        QMessageBox.information(
            self,
            "Transcription Complete",
            f"Transcription saved to:\n{output_path}\n\n"
            f"Text length: {len(text)} characters"
        )
    
    @Slot(str, str)
    def _show_error(self, title: str, message: str) -> None:
        """Show error dialog."""
        QMessageBox.critical(self, title, message)
    
    @Slot(bool)
    def _set_widgets_enabled(self, enabled: bool) -> None:
        """Enable/disable widgets."""
        self.select_file_button.setEnabled(enabled)
        self.load_model_button.setEnabled(enabled)
        self.settings_button.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.quant_combo.setEnabled(enabled)
        self.device_combo.setEnabled(enabled)
        self.language_combo.setEnabled(enabled)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            # Check if at least one file is a video or audio file
            urls = event.mimeData().urls()
            for url in urls:
                file_path = Path(url.toLocalFile())
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    video_formats = [".mp4", ".avi", ".mkv", ".webm", ".mov", ".flv", ".wmv", ".m4v"]
                    audio_formats = [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"]
                    if suffix in video_formats or suffix in audio_formats:
                        event.acceptProposedAction()
                        return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        urls = event.mimeData().urls()
        if not urls:
            return
        
        # Get the first valid file
        for url in urls:
            file_path = Path(url.toLocalFile())
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                video_formats = [".mp4", ".avi", ".mkv", ".webm", ".mov", ".flv", ".wmv", ".m4v"]
                audio_formats = [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"]
                if suffix in video_formats or suffix in audio_formats:
                    logger.info(f"Dropped file: {file_path}")
                    self._ask_transcription_mode(file_path)
                    event.acceptProposedAction()
                    return
        
        event.ignore()
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.controller.cleanup()
        logger.info("Application closing")
        super().closeEvent(event)

