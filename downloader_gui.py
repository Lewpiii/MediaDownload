from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import sys
import os
from pathlib import Path
import requests
from datetime import datetime

class DownloaderWindow(QMainWindow):
    def __init__(self, files_to_download):
        super().__init__()
        self.files = files_to_download
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Discord Media Downloader")
        self.setMinimumSize(600, 400)
        
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2d31;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #5865f2;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                margin: 4px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #40444b;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5865f2;
                border-radius: 4px;
            }
        """) 

        # Liste des fichiers
        self.files_list = QListWidget()
        self.files_list.setStyleSheet("""
            QListWidget {
                background-color: #36393f;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                background-color: #40444b;
                border-radius: 4px;
                margin: 2px;
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #454950;
            }
        """)
        layout.addWidget(self.files_list)

        # Progress section
        progress_group = QGroupBox("�� Progress")
        progress_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #40444b;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Waiting...")
        self.speed_label = QLabel("")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.speed_label)
        layout.addWidget(progress_group)

        # Folder selection
        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        self.folder_path = QLineEdit(str(Path.home() / "Downloads" / "MediaDownload"))
        browse_btn = QPushButton("📂 Browse")
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_widget)

        # Action buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        self.start_btn = QPushButton("▶️ Start")
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addWidget(buttons_widget)

        # Connexions
        browse_btn.clicked.connect(self.browse_folder)
        self.start_btn.clicked.connect(self.start_download)
        self.cancel_btn.clicked.connect(self.cancel_download)

        # Initialiser la liste des fichiers
        self.populate_files_list()

    def populate_files_list(self):
        """Remplit la liste des fichiers avec aperçus"""
        for file in self.files:
            # Créer un widget personnalisé pour chaque fichier
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            
            # Icône selon le type de fichier
            icon_label = QLabel()
            if file.filename.lower().endswith(('.mp4', '.webm', '.mov')):
                icon_label.setText("🎥")
            else:
                icon_label.setText("🖼️")
            item_layout.addWidget(icon_label)
            
            # Nom du fichier
            name_label = QLabel(file.filename)
            name_label.setStyleSheet("color: white;")
            item_layout.addWidget(name_label)
            
            # Taille du fichier
            size_str = self._format_size(file.size)
            size_label = QLabel(size_str)
            size_label.setStyleSheet("color: #a0a0a0;")
            item_layout.addWidget(size_label)
            
            # Ajouter à la liste
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.files_list.addItem(item)
            self.files_list.setItemWidget(item, item_widget)

    def _format_size(self, size):
        """Formate la taille en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def browse_folder(self):
        """Opens folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Download Folder",
            self.folder_path.text()
        )
        if folder:
            self.folder_path.setText(folder)

    def start_download(self):
        """Starts downloading files"""
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.download_progress = 0
        self.total_size = sum(file.size for file in self.files)
        self.start_time = datetime.now()
        
        # Créer le dossier de destination
        os.makedirs(self.folder_path.text(), exist_ok=True)
        
        # Notification de début
        if hasattr(self, 'systray'):
            self.systray.showMessage(
                "Download Started",
                f"Downloading {len(self.files)} files...",
                QSystemTrayIcon.MessageIcon.Information
            )
        
        # Démarrer le téléchargement
        self.current_file_index = 0
        self.download_next_file()

    def download_next_file(self):
        """Télécharge le fichier suivant"""
        if self.current_file_index >= len(self.files):
            self.download_complete()
            return
            
        file = self.files[self.current_file_index]
        destination = Path(self.folder_path.text()) / file.filename
        
        # Créer la requête
        response = requests.get(file.url, stream=True)
        if response.status_code == 200:
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        self.update_progress(len(chunk))
        
        self.current_file_index += 1
        self.download_next_file()

    def update_progress(self, chunk_size):
        """Met à jour la progression du téléchargement"""
        self.download_progress += chunk_size
        percentage = (self.download_progress / self.total_size) * 100
        
        # Calculer la vitesse
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        speed = self.download_progress / elapsed_time if elapsed_time > 0 else 0
        
        # Estimer le temps restant
        remaining_bytes = self.total_size - self.download_progress
        remaining_time = remaining_bytes / speed if speed > 0 else 0
        
        # Mettre à jour l'interface
        self.progress_bar.setValue(int(percentage))
        self.speed_label.setText(f"{self._format_size(speed)}/s")
        self.progress_label.setText(
            f"{self._format_size(self.download_progress)} / {self._format_size(self.total_size)} "
            f"({int(percentage)}%) - {int(remaining_time)} seconds remaining"
        )

    def cancel_download(self):
        """Cancels current download"""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Download cancelled")
        
        if hasattr(self, 'systray'):
            self.systray.showMessage(
                "Download Cancelled",
                "The download was cancelled by user.",
                QSystemTrayIcon.MessageIcon.Warning
            )

    def download_complete(self):
        """Handles download completion"""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Download complete!")
        
        if hasattr(self, 'systray'):
            self.systray.showMessage(
                "Download Complete",
                f"Files have been downloaded to {self.folder_path.text()}",
                QSystemTrayIcon.MessageIcon.Information
            )
        
        reply = QMessageBox.question(
            self,
            "Download Complete",
            "Do you want to open the destination folder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.open_destination_folder()

    def open_destination_folder(self):
        """Ouvre le dossier de destination"""
        path = self.folder_path.text()
        if os.path.exists(path):
            # Ouvrir le dossier selon le système d'exploitation
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{path}"')
            else:  # Linux
                os.system(f'xdg-open "{path}"')

    def closeEvent(self, event):
        """Handles window closing"""
        if hasattr(self, 'current_file_index'):
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A download is in progress. Do you really want to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def show_downloader(files):
    """Affiche la fenêtre de téléchargement"""
    app = QApplication.instance() or QApplication(sys.argv)
    window = DownloaderWindow(files)
    window.show()
    return app.exec() 