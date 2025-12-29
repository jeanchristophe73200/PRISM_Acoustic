from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from utils.logger import log

class InspectorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inspection : Audio & Météo")
        self.setGeometry(200, 200, 1000, 700)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # En-tête
        header = QLabel("Vue Inspection (Fichier Audio chargé)")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # --- Zone Graphique (Audio + Spectro) ---
        self.figure, (self.ax_wave, self.ax_spec) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        self.figure.patch.set_facecolor('#1e1e1e')
        
        # Style des axes
        for ax in [self.ax_wave, self.ax_spec]:
            ax.set_facecolor('black')
            ax.tick_params(axis='x', colors='gray')
            ax.tick_params(axis='y', colors='gray')
            ax.spines['bottom'].set_color('gray')
            ax.spines['top'].set_color('gray')
            ax.spines['left'].set_color('gray')
            ax.spines['right'].set_color('gray')

        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # --- Barre de Contrôle ---
        control_bar = QFrame()
        control_bar.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; margin-top: 10px;")
        control_layout = QHBoxLayout(control_bar)
        
        self.btn_play = QPushButton("▶ LECTURE")
        self.btn_play.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px; border: none; font-weight: bold;")
        
        self.lbl_time = QLabel("00:00.000")
        self.lbl_time.setStyleSheet("color: #3498db; font-family: monospace; font-size: 16px;")

        control_layout.addWidget(self.btn_play)
        control_layout.addWidget(self.lbl_time)
        layout.addWidget(control_bar)

        self.plot_dummy_data()
        
        log.info("Fenêtre InspectorWindow initialisée avec succès.")

    def plot_dummy_data(self):
        """Génère un affichage test pour valider que matplotlib fonctionne"""
        try:
            # Audio fictif (bruit blanc + sinus)
            t = np.linspace(0, 10, 44100 * 10)
            audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.normal(0, 1, len(t))
            
            # Plot Waveform
            self.ax_wave.clear()
            self.ax_wave.plot(t[::100], audio[::100], color='cyan', linewidth=0.5)
            self.ax_wave.set_title("Amplitude", color='gray', fontsize=10)
            self.ax_wave.set_ylim(-1, 1)

            # Plot Spectrogram
            self.ax_spec.clear()
            self.ax_spec.specgram(audio[:44100*2], NFFT=1024, Fs=44100, noverlap=512, cmap='inferno')
            self.ax_spec.set_title("Spectrogramme", color='gray', fontsize=10)
            self.ax_spec.set_xlabel("Temps (s)", color='gray')
            
            self.canvas.draw()
            log.info("Données graphiques factices tracées.")
        except Exception as e:
            log.error(f"Erreur lors du tracé dummy: {e}", exc_info=True)

