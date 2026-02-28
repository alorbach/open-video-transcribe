"""Main window for Open Video Transcribe."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QComboBox, QHBoxLayout, QGroupBox
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from core.controller import Controller
from core.logging_config import get_logger
from core.models.model_info import (
    get_models_sorted_by_rating,
    get_model_info,
    is_model_cached,
    get_gpu_vram_mb,
    resolve_repo,
)
from config.manager import config_manager
from gui.progress_dialog import ProgressDialog
from gui.settings_dialog import SettingsDialog

logger = get_logger(__name__)


class ModelLoadThread(QThread):
    """Thread to load model without blocking the GUI."""
    finished = Signal(bool, str)

    def __init__(self, controller, model_type: str, model_name: str, quantization: str, device: str):
        super().__init__()
        self.controller = controller
        self.model_type = model_type
        self.model_name = model_name
        self.quantization = quantization
        self.device = device

    def run(self) -> None:
        success = self.controller.load_model(
            self.model_type,
            self.model_name,
            self.quantization,
            self.device,
        )
        if success:
            self.finished.emit(True, f"Model {self.model_name} ready")
        else:
            self.finished.emit(False, "Model load failed")


class ModelDownloadThread(QThread):
    """Thread to pre-download model without loading."""
    finished = Signal(bool, str)

    def __init__(self, model_id: str, quantization: str):
        super().__init__()
        self.model_id = model_id
        self.quantization = quantization

    def run(self) -> None:
        try:
            from faster_whisper.utils import download_model
            repo_or_id, use_systran = resolve_repo(self.model_id, self.quantization)
            download_model(repo_or_id)
            self.finished.emit(True, f"Model {self.model_id} downloaded successfully")
        except Exception as e:
            logger.exception("Model download failed")
            self.finished.emit(False, str(e))


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
        
        self.controller = Controller(cuda_available=cuda_available)
        self.cuda_available = cuda_available
        self.progress_dialog: ProgressDialog = None
        self._load_thread: Optional[ModelLoadThread] = None
        self._download_thread: Optional[ModelDownloadThread] = None
        
        self.setWindowTitle("Open Video Transcribe")
        self.setFixedSize(500, 480)
        
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
        for info in get_models_sorted_by_rating():
            self.model_combo.addItem(info.combo_display(), info.id)
        self.model_combo.currentIndexChanged.connect(self._on_model_selection_changed)
        model_row.addWidget(self.model_combo)
        model_layout.addLayout(model_row)
        
        self.model_desc_label = QLabel("")
        self.model_desc_label.setWordWrap(True)
        self.model_desc_label.setStyleSheet("color: gray; font-size: 11px;")
        model_layout.addWidget(self.model_desc_label)
        
        quant_row = QHBoxLayout()
        quant_row.addWidget(QLabel("Quantization:"))
        self.quant_combo = QComboBox()
        self.quant_combo.addItems(["float16", "float32", "int8"])
        self.quant_combo.currentIndexChanged.connect(self._on_model_selection_changed)
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
        
        self.download_model_button = QPushButton("Download Model")
        self.download_model_button.clicked.connect(self._download_model)
        self.download_model_button.setToolTip("Pre-download model without loading")
        button_row.addWidget(self.download_model_button)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._show_settings)
        button_row.addWidget(self.settings_button)
        
        layout.addLayout(button_row)
        
        self._connect_signals()
        self._load_config()
        self._on_model_selection_changed()
        
        logger.info("MainWindow initialized")
    
    def _connect_signals(self) -> None:
        """Connect controller signals."""
        self.controller.status_updated.connect(self._update_status)
        self.controller.progress_updated.connect(self._update_progress)
        self.controller.transcription_completed.connect(self._on_transcription_completed)
        self.controller.error_occurred.connect(self._show_error)
        self.controller.widgets_enabled.connect(self._set_widgets_enabled)
    
    def _on_model_selection_changed(self) -> None:
        """Update description label when model selection changes."""
        model_id = self.model_combo.currentData()
        if not model_id:
            self.model_desc_label.setText("")
            return
        info = get_model_info(model_id)
        if not info:
            self.model_desc_label.setText("")
            return
        desc = info.description_with_rating()
        gpu_vram = get_gpu_vram_mb()
        if gpu_vram is not None and info.vram_mb > 0:
            status = "OK" if gpu_vram >= info.vram_mb else "may be tight"
            desc += f" Your GPU: {gpu_vram} MB ({status})."
        quant = self.quant_combo.currentText()
        repo_or_id, _ = resolve_repo(model_id, quant)
        if is_model_cached(repo_or_id):
            desc += " [Cached]"
        self.model_desc_label.setText(desc)
        self.model_combo.setToolTip(info.description)

    def _load_config(self) -> None:
        """Load configuration."""
        model_name = self.controller.current_model_name or "large-v3"
        found = False
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == model_name:
                self.model_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.model_combo.setCurrentIndex(0)
        
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
        """Ask user if they want full transcription, test mode, or lyrics extraction."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Transcription Mode")
        msg_box.setText("Choose transcription mode:")
        msg_box.setInformativeText(
            "Full File: Transcribe the entire file\n"
            "Test Mode: Transcribe only first 5 minutes\n"
            "Extract Lyrics: Word-level timestamps for MP3/WAV (format: START=END=WORD)"
        )
        
        full_button = msg_box.addButton("Full File", QMessageBox.ButtonRole.AcceptRole)
        test_button = msg_box.addButton("Test Mode (5 min)", QMessageBox.ButtonRole.AcceptRole)
        lyrics_button = msg_box.addButton("Extract Lyrics", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.setDefaultButton(full_button)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_button:
            return
        elif clicked_button == test_button:
            logger.info("Starting transcription in test mode (5 minutes)")
            self.controller.transcribe_file(file_path, test_mode=True)
        elif clicked_button == lyrics_button:
            logger.info("Starting lyrics extraction mode")
            self.controller.transcribe_file(file_path, test_mode=False, lyrics_mode=True)
        else:
            logger.info("Starting full file transcription")
            self.controller.transcribe_file(file_path, test_mode=False)
    
    @Slot()
    def _load_model(self) -> None:
        """Load transcription model (runs in background thread)."""
        model_id = self.model_combo.currentData()
        if not model_id:
            return
        quantization = self.quant_combo.currentText()
        device = self.device_combo.currentText()
        
        self._set_widgets_enabled(False)
        if self.progress_dialog is None:
            self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.setWindowTitle("Loading Model")
        self.progress_dialog.update_progress(0.0, f"Loading {model_id}...")
        self.progress_dialog.show()
        
        self._load_thread = ModelLoadThread(
            self.controller, "whisper", model_id, quantization, device
        )

        def on_finished(success: bool, msg: str) -> None:
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            self._set_widgets_enabled(True)
            self._load_thread = None
            if success:
                self.status_label.setText(msg)
            else:
                QMessageBox.warning(self, "Load Failed", msg)

        self._load_thread.finished.connect(on_finished)
        self._load_thread.start()

    @Slot()
    def _download_model(self) -> None:
        """Pre-download model without loading."""
        model_id = self.model_combo.currentData()
        if not model_id:
            return
        quantization = self.quant_combo.currentText()
        
        self.download_model_button.setEnabled(False)
        if self.progress_dialog is None:
            self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.setWindowTitle("Download Model")
        self.progress_dialog.update_progress(0.0, f"Downloading {model_id}...")
        self.progress_dialog.show()
        
        self._download_thread = ModelDownloadThread(model_id, quantization)

        def on_finished(success: bool, msg: str) -> None:
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            self.download_model_button.setEnabled(True)
            self._download_thread = None
            if success:
                QMessageBox.information(self, "Download Complete", msg)
                self._on_model_selection_changed()
            else:
                QMessageBox.warning(self, "Download Failed", msg)

        self._download_thread.finished.connect(on_finished)
        self._download_thread.start()
    
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
        self.download_model_button.setEnabled(enabled)
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
        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.requestInterruption()
            self._load_thread.wait(5000)
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.requestInterruption()
            self._download_thread.wait(5000)
        self.controller.cleanup()
        logger.info("Application closing")
        super().closeEvent(event)

