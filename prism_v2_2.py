import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, QSlider)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPainter, QPen, QColor
import scipy.io.wavfile as wav

# --- CONFIGURATION ---
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024
FFT_SIZE = 2048
HISTORY_SIZE = 500   
FREQ_TOLERANCE = 3.0 

class AudioAnalyzer(QThread):
    def __init__(self):
        super().__init__()
        self.target_freq = 50.0

    def analyze_chunk(self, audio_chunk, target_freq):
        if len(audio_chunk) < FFT_SIZE: return 0.0
        window = np.hanning(len(audio_chunk))
        audio_windowed = audio_chunk * window
        fft_result = np.fft.rfft(audio_windowed, n=FFT_SIZE)
        magnitudes = np.abs(fft_result)
        freqs = np.fft.rfftfreq(FFT_SIZE, d=1/SAMPLE_RATE)
        
        # Tolérance de fréquence (Vision élargie)
        idx_min = (np.abs(freqs - (target_freq - FREQ_TOLERANCE))).argmin()
        idx_max = (np.abs(freqs - (target_freq + FREQ_TOLERANCE))).argmin()
        if idx_min == idx_max: idx_max += 1
        
        magnitude_target = np.max(magnitudes[idx_min:idx_max])
        val_db = 20 * np.log10(magnitude_target + 1e-9)
        return max(0, val_db + 20)

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y_scale = h / 100.0
        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))
        
        # Seuil Violet
        thresh_y = h - (self.threshold * y_scale)
        painter.setPen(QPen(QColor(180, 0, 255), 2))
        painter.drawLine(0, int(thresh_y), w, int(thresh_y))

        # Signal Vert
        painter.setPen(QPen(QColor(0, 255, 0), 1))
        path = []
        for i, val in enumerate(self.data):
            x = (i / HISTORY_SIZE) * w
            y = h - (val * y_scale)
            path.append((x, y))
        for i in range(len(path) - 1):
            painter.drawLine(int(path[i][0]), int(path[i][1]), int(path[i+1][0]), int(path[i+1][1]))

        # Barres Rouges
        for i, status in enumerate(self.detections):
            if status > 0:
                x = int((i / HISTORY_SIZE) * w)
                bw = int((w / HISTORY_SIZE) + 1)
                if status == 2: painter.fillRect(x, 0, bw, h, QColor(255, 0, 0, 100)) # Onyx
                elif status == 1: painter.fillRect(x, h-10, bw, 10, QColor(255, 0, 0)) # Auto

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prism V2.2 - Calibration")
        self.resize(1200, 600)
        self.audio_data = np.array([])
        self.sample_rate = 44100
        self.duration = 0
        self.onyx_markers = []
        self.analyzer = AudioAnalyzer()
        
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        self.spectro = SpectrogramWidget()
        layout.addWidget(self.spectro)
        
        ctrl = QHBoxLayout()
        btn_load = QPushButton("1. Charger Audio")
        btn_load.clicked.connect(self.load_audio)
        ctrl.addWidget(btn_load)
        btn_csv = QPushButton("2. Charger CSV")
        btn_csv.clicked.connect(self.load_csv)
        ctrl.addWidget(btn_csv)
        
        self.lbl_freq = QLabel("Fréq: 50Hz")
        self.sl_freq = QSlider(Qt.Orientation.Horizontal)
        self.sl_freq.setRange(20, 2000)
        self.sl_freq.setValue(50)
        self.sl_freq.valueChanged.connect(self.update_freq)
        ctrl.addWidget(self.lbl_freq)
        ctrl.addWidget(self.sl_freq)

        self.lbl_thresh = QLabel("Seuil: 30")
        self.sl_thresh = QSlider(Qt.Orientation.Horizontal)
        self.sl_thresh.setRange(0, 100)
        self.sl_thresh.setValue(30)
        self.sl_thresh.valueChanged.connect(lambda v: [self.lbl_thresh.setText(f"Seuil: {v}"), setattr(self.spectro, 'threshold', v)])
        ctrl.addWidget(self.lbl_thresh)
        ctrl.addWidget(self.sl_thresh)
        layout.addLayout(ctrl)
        
        self.lbl_time = QLabel("00:00")
        layout.addWidget(self.lbl_time)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.on_position_changed)
        
        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.process)

    def load_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Audio", "", "*.wav")
        if path:
            self.player.setSource(QUrl.fromLocalFile(path))
            try:
                self.sample_rate, self.audio_data = wav.read(path)
                if len(self.audio_data.shape) > 1: self.audio_data = self.audio_data.mean(axis=1)
                self.duration = len(self.audio_data) / self.sample_rate
                self.player.play()
                self.timer.start()
            except: pass
        self.setFocus()

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV", "", "*.csv")
        if not path: return
        try:
            df = pd.read_csv(path, sep=None, engine='python', comment='#', encoding='latin1')
            df.columns = df.columns.str.strip()
            df_tags = df[df['note'].notna()]
            start_ts = df['ts'].iloc[0]
            self.onyx_markers = (df_tags['ts'] - start_ts).tolist()
            print(f"--- {len(self.onyx_markers)} Marqueurs chargés ---")
            for t, n in zip(self.onyx_markers, df_tags['note']):
                print(f"Tag à {t:.1f}s : {n}")
        except Exception as e: print(f"Erreur CSV: {e}")
        self.setFocus()

    def update_freq(self, val):
        self.lbl_freq.setText(f"Fréq: {val}Hz")
        self.analyzer.target_freq = float(val)
        self.setFocus()

    def process(self):
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState: return
        pos_sec = self.player.position() / 1000.0
        val = 0
        if len(self.audio_data) > 0:
            idx = int(pos_sec * self.sample_rate)
            chunk = self.audio_data[idx:idx+CHUNK_SIZE]
            val = self.analyzer.analyze_chunk(chunk, self.analyzer.target_freq)
        is_onyx = any(abs(pos_sec - m) < 1.0 for m in self.onyx_markers)
        is_detected = val > self.spectro.threshold
        self.spectro.add_slice(val, is_detected, is_onyx)

    def on_position_changed(self, pos):
        self.lbl_time.setText(f"{pos//1000//60:02}:{pos//1000%60:02}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
            else: self.player.play()
        elif event.key() == Qt.Key.Key_Right: self.player.setPosition(self.player.position() + 60000)
        elif event.key() == Qt.Key.Key_Left: self.player.setPosition(self.player.position() - 60000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
