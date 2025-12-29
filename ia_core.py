import sys
import numpy as np
import csv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, QSlider, QMessageBox)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPainter, QPen, QColor
import scipy.io.wavfile as wav

# --- CONFIGURATION STANDARD ---
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024
FFT_SIZE = 2048
HISTORY_SIZE = 500   

class AudioAnalyzer(QThread):
    def __init__(self):
        super().__init__()
        self.target_freq = 50.0 # Par defaut

    def analyze_chunk(self, audio_chunk, target_freq):
        """Analyse FFT simple et robuste"""
        if len(audio_chunk) < FFT_SIZE: return 0.0

        # Fenetrage
        window = np.hanning(len(audio_chunk))
        audio_windowed = audio_chunk * window

        # FFT
        fft_result = np.fft.rfft(audio_windowed, n=FFT_SIZE)
        magnitudes = np.abs(fft_result)
        freqs = np.fft.rfftfreq(FFT_SIZE, d=1/SAMPLE_RATE)

        # Tolerance elargie (+/- 3 Hz) pour ne pas rater le signal
        idx_min = (np.abs(freqs - (target_freq - 3.0))).argmin()
        idx_max = (np.abs(freqs - (target_freq + 3.0))).argmin()
        if idx_min == idx_max: idx_max += 1
        
        magnitude_target = np.max(magnitudes[idx_min:idx_max])

        # Conversion dB visuelle
        val_db = 20 * np.log10(magnitude_target + 1e-9)
        normalized = max(0, val_db + 20) 
        return normalized

class SpectrogramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.setStyleSheet("background-color: #2b2b2b;")
        self.data = [0.0] * HISTORY_SIZE
        self.detections = [0] * HISTORY_SIZE 
        self.threshold = 30.0

    def add_slice(self, value, is_detected, is_onyx_marker=False):
        self.data.pop(0)
        self.data.append(value)
        
        status = 0
        if is_onyx_marker: status = 2
        elif is_detected: status = 1
        
        self.detections.pop(0)
        self.detections.append(status)
        self.update()

    def set_threshold(self, val):
        self.threshold = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y_scale = h / 100.0

        # Fond
        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))
        
        # Seuil (Ligne Violette)
        thresh_y = h - (self.threshold * y_scale)
        painter.setPen(QPen(QColor(180, 0, 255), 2))
        painter.drawLine(0, int(thresh_y), w, int(thresh_y))

        # Signal (Ligne Verte)
        painter.setPen(QPen(QColor(0, 255, 0), 1))
        path = []
        for i, val in enumerate(self.data):
            x = (i / HISTORY_SIZE) * w
            y = h - (val * y_scale)
            path.append((x, y))
        
        for i in range(len(path) - 1):
            painter.drawLine(int(path[i][0]), int(path[i][1]), int(path[i+1][0]), int(path[i+1][1]))

        # Marqueurs (Barres Rouges)
        for i, status in enumerate(self.detections):
            if status > 0:
                x = int((i / HISTORY_SIZE) * w)
                bw = int((w / HISTORY_SIZE) + 1)
                # Onyx = Rouge Translucide (Haut en bas)
                if status == 2: 
                    painter.fillRect(x, 0, bw, h, QColor(255, 0, 0, 100))
                # Detection Auto = Tiret Rouge (Bas)
                elif status == 1: 
                    painter.fillRect(x, h-10, bw, 10, QColor(255, 0, 0))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prism V2.3 - Stable Core")
        self.resize(1200, 600)

        # Variables
        self.audio_data = np.array([])
        self.sample_rate = 44100
        self.duration = 0
        self.onyx_markers = []
        self.csv_start_ts = 0.0
        
        # Moteurs
        self.analyzer = AudioAnalyzer()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        
        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.process_audio_visual)

        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Graphique
        self.spectro = SpectrogramWidget()
        layout.addWidget(self.spectro)

        # Contrôles
        controls = QHBoxLayout()
        
        btn_load = QPushButton("1. Charger WAV")
        btn_load.clicked.connect(self.load_audio)
        controls.addWidget(btn_load)
        
        btn_csv = QPushButton("2. Charger CSV Onyx")
        btn_csv.clicked.connect(self.load_csv)
        controls.addWidget(btn_csv)

        self.lbl_freq = QLabel("Fréquence: 50 Hz")
        self.slider_freq = QSlider(Qt.Orientation.Horizontal)
        self.slider_freq.setRange(20, 2000)
        self.slider_freq.setValue(50)
        self.slider_freq.valueChanged.connect(self.change_freq)
        controls.addWidget(self.lbl_freq)
        controls.addWidget(self.slider_freq)

        self.lbl_thresh = QLabel("Seuil: 30")
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setRange(0, 100)
        self.slider_thresh.setValue(30)
        self.slider_thresh.valueChanged.connect(self.change_thresh)
        controls.addWidget(self.lbl_thresh)
        controls.addWidget(self.slider_thresh)

        btn_play = QPushButton("Play / Pause (Espace)")
        btn_play.clicked.connect(self.toggle_play)
        controls.addWidget(btn_play)

        layout.addLayout(controls)

        # Barre de temps
        self.lbl_time = QLabel("00:00 / 00:00")
        layout.addWidget(self.lbl_time)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.sliderMoved.connect(self.set_position)
        layout.addWidget(self.seek_slider)

        # Focus clavier
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def load_audio(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Ouvrir Audio (WAV)", "", "WAV Files (*.wav)")
        if file_name:
            # 1. Chargement Lecteur (Joue tout)
            self.player.setSource(QUrl.fromLocalFile(file_name))
            
            # 2. Chargement Données Brutes (Pour Analyse Graphique)
            try:
                self.sample_rate, self.audio_data = wav.read(file_name)
                # Conversion Mono si Stereo
                if len(self.audio_data.shape) > 1:
                    self.audio_data = self.audio_data.mean(axis=1)
                
                self.btn_play = self.sender() # Hack pour focus
                self.setFocus() # Rendre la main au clavier
                print("Audio WAV chargé avec succès pour analyse.")
                
            except Exception as e:
                print(f"ERREUR: Impossible d'analyser ce fichier. Est-ce bien un WAV ? ({e})")
                QMessageBox.warning(self, "Format Non Supporté", 
                                    "Prism (Version Calibration) a besoin d'un fichier .WAV pour dessiner le graphique.\n\n"
                                    "Le fichier FLAC peut être lu, mais le graphique vert restera plat.")
                self.audio_data = np.array([]) # Vide

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Ouvrir CSV Onyx", "", "CSV Files (*.csv)")
        if not file_name: return

        self.onyx_markers = []
        try:
            # Lecture robuste CSV standard
            with open(file_name, 'r', encoding='latin1') as f:
                # Detecter le separateur (Virgule ou Point-Virgule)
                dialect = csv.Sniffer().sniff(f.read(1024))
                f.seek(0)
                reader = csv.reader(f, dialect)
                
                rows = list(reader)
                if not rows: return

                # Trouver les index
                header = rows[0] # Ou ligne suivante si commentaire...
                # Onyx met parfois des commentaires au debut. On cherche la ligne headers
                start_row = 0
                for i, row in enumerate(rows):
                    if 'ts' in row or 'ts ' in row:
                        header = [h.strip() for h in row]
                        start_row = i + 1
                        break
                
                try:
                    idx_ts = header.index('ts')
                    idx_note = header.index('note')
                except ValueError:
                    print("Colonnes 'ts' ou 'note' introuvables dans le CSV.")
                    return

                # Parser les donnees
                start_ts_val = None
                count = 0
                
                for row in rows[start_row:]:
                    if len(row) <= idx_note: continue
                    try:
                        ts_val = float(row[idx_ts])
                        note_val = row[idx_note].strip()
                        
                        if start_ts_val is None: start_ts_val = ts_val
                        
                        # Si note n'est pas vide et pas NaN
                        if note_val and note_val.lower() != 'nan':
                            rel_time = ts_val - start_ts_val
                            self.onyx_markers.append(rel_time)
                            count += 1
                            print(f"Tag Onyx: {note_val} à {rel_time:.1f}s")
                            
                    except ValueError: continue
                    
            print(f"--- {count} Marqueurs importés ---")
            self.setFocus()
            
        except Exception as e:
            print(f"Erreur lecture CSV: {e}")

    def process_audio_visual(self):
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState: return
        
        pos_ms = self.player.position()
        pos_sec = pos_ms / 1000.0
        
        # 1. Analyse Spectrale
        val = 0.0
        if self.audio_data.size > 0:
            idx = int(pos_sec * self.sample_rate)
            chunk = self.audio_data[idx : idx + CHUNK_SIZE]
            val = self.analyzer.analyze_chunk(chunk, self.analyzer.target_freq)

        # 2. Logic Seuils
        is_detected = (val > self.spectro.threshold)
        is_onyx = any(abs(pos_sec - m) < 1.0 for m in self.onyx_markers)
        
        self.spectro.add_slice(val, is_detected, is_onyx)

    # --- Utilitaires ---
    def change_freq(self, val):
        self.lbl_freq.setText(f"Fréquence: {val} Hz")
        self.analyzer.target_freq = float(val)
        self.setFocus()

    def change_thresh(self, val):
        self.lbl_thresh.setText(f"Seuil: {val}")
        self.spectro.set_threshold(float(val))
        self.setFocus()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            self.timer.start()
        self.setFocus()

    def on_position_changed(self, pos):
        self.seek_slider.setValue(pos)
        s = pos // 1000
        d = self.duration // 1000
        self.lbl_time.setText(f"{s//60:02}:{s%60:02} / {d//60:02}:{d%60:02}")

    def on_duration_changed(self, dur):
        self.duration = dur
        self.seek_slider.setRange(0, dur)

    def set_position(self, pos):
        self.player.setPosition(pos)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key.Key_Right:
            self.player.setPosition(self.player.position() + 60000)
        elif event.key() == Qt.Key.Key_Left:
            self.player.setPosition(self.player.position() - 60000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
