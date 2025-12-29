import os
import pandas as pd
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                             QLabel, QMessageBox, QTextEdit, QInputDialog, QComboBox, QDialog, QCheckBox, QSplitter)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QPainterPath
from utils.logger import log

# --- Fenêtre Apprentissage ---
class LearningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Expertise")
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Classification de l'événement :")
        self.layout.addWidget(self.label)
        self.combo = QComboBox()
        self.combo.addItems(["PAC/VMC (Stationnaire)", "Vent (Aléatoire)", "Trafic Routier", "Aérien", "Voix/Voisinage", "Industrie", "Autre"])
        self.layout.addWidget(self.combo)
        self.btn_ok = QPushButton("Valider")
        self.btn_ok.clicked.connect(self.accept)
        self.layout.addWidget(self.btn_ok)
    def get_label(self): return self.combo.currentText()

# --- DASHBOARD V9.1 ---
class Dashboard(QWidget):
    def __init__(self, ia_interface=None):
        super().__init__()
        self.ia = ia_interface
        self.main_layout = QVBoxLayout(self)

        # 1. TOOLBAR
        self.toolbar_layout = QHBoxLayout()
        btn_style = "padding: 5px; font-size: 11px; border-radius: 3px; color: white; font-weight: bold;"
        
        self.btn_load = QPushButton("1. CHARGER")
        self.btn_load.setStyleSheet(btn_style + "background-color: #007AFF;")
        self.btn_load.clicked.connect(self.select_folder)
        self.toolbar_layout.addWidget(self.btn_load)

        self.btn_scan = QPushButton("2. SCAN EXPERT")
        self.btn_scan.setStyleSheet(btn_style + "background-color: #FF3B30;")
        self.btn_scan.clicked.connect(self.run_auto_scan)
        self.toolbar_layout.addWidget(self.btn_scan)

        self.btn_prev = QPushButton("<<")
        self.btn_prev.setStyleSheet(btn_style + "background-color: #555555;")
        self.btn_prev.clicked.connect(self.prev_event)
        self.toolbar_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton(">>")
        self.btn_next.setStyleSheet(btn_style + "background-color: #555555;")
        self.btn_next.clicked.connect(self.next_event)
        self.toolbar_layout.addWidget(self.btn_next)

        self.btn_learn = QPushButton("3. QUALIFIER")
        self.btn_learn.setStyleSheet(btn_style + "background-color: #34C759;")
        self.btn_learn.clicked.connect(self.teach_ai)
        self.toolbar_layout.addWidget(self.btn_learn)

        self.main_layout.addLayout(self.toolbar_layout)

        # 2. FILTRES HAUT
        self.filter_layout = QHBoxLayout()
        self.lbl_filtres = QLabel("Haut (Superposition) :")
        self.lbl_filtres.setStyleSheet("color: #AAA; font-size: 11px;")
        self.filter_layout.addWidget(self.lbl_filtres)

        self.filters_config = [
            {"label": "40Hz", "color": "#d633ff", "col_match": "40hz"},
            {"label": "50Hz", "color": "#ff9933", "col_match": "50hz"},
            {"label": "63Hz", "color": "#ffff00", "col_match": "63hz"},
            {"label": "80Hz", "color": "#dddddd", "col_match": "80hz"},
            {"label": "100Hz", "color": "#ffb6c1", "col_match": "100hz"},
            {"label": "125Hz", "color": "#00ffff", "col_match": "125hz"},
            {"label": "160Hz", "color": "#8a2be2", "col_match": "160hz"},
        ]
        
        self.checkboxes = {}
        for f in self.filters_config:
            cb = QCheckBox(f["label"])
            cb.setStyleSheet(f"color: {f['color']}; font-weight: bold; font-size: 10px;")
            cb.stateChanged.connect(self.update_main_curves)
            self.filter_layout.addWidget(cb)
            self.checkboxes[f["col_match"]] = cb
        
        self.filter_layout.addStretch()
        self.main_layout.addLayout(self.filter_layout)

        # 3. FILTRES BAS (Glissant 5s)
        self.rta_controls = QHBoxLayout()
        self.lbl_rta = QLabel("Bas (Spectre - Rolling 5s) :")
        self.lbl_rta.setStyleSheet("color: #AAA; font-size: 11px;")
        self.rta_controls.addWidget(self.lbl_rta)

        self.cb_rta_avg = QCheckBox("Moyenne 5s (Vert)")
        self.cb_rta_avg.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 10px;")
        self.cb_rta_avg.setChecked(True)
        self.cb_rta_avg.stateChanged.connect(lambda: self.update_spectrum(self.last_hover_ts))
        self.rta_controls.addWidget(self.cb_rta_avg)

        self.cb_rta_peak = QCheckBox("Crêtes 5s (Cyan)")
        self.cb_rta_peak.setStyleSheet("color: cyan; font-weight: bold; font-size: 10px;")
        self.cb_rta_peak.setChecked(True)
        self.cb_rta_peak.stateChanged.connect(lambda: self.update_spectrum(self.last_hover_ts))
        self.rta_controls.addWidget(self.cb_rta_peak)

        self.rta_controls.addStretch()
        self.main_layout.addLayout(self.rta_controls)

        # 4. SPLITTER
        self.splitter = QSplitter(Qt.Vertical)
        
        # --- GRAPH 1 ---
        pg.setConfigOption('background', '#1e1e1e')
        self.graph_time = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.graph_time.showGrid(x=True, y=True, alpha=0.3)
        self.graph_time.setLabel('left', 'Niveau (dB)')
        self.playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('r', width=1))
        self.graph_time.addItem(self.playhead)
        
        self.graph_time.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.graph_time.scene().sigMouseClicked.connect(self.on_graph_click)
        
        self.splitter.addWidget(self.graph_time)

        # --- GRAPH 2 (Spectre) ---
        self.graph_spectrum = pg.PlotWidget()
        self.graph_spectrum.setLabel('bottom', 'Fréquence (Hz)')
        self.graph_spectrum.setLabel('left', 'dB')
        self.graph_spectrum.showGrid(x=True, y=True, alpha=0.5)
        self.graph_spectrum.setYRange(0, 90)
        self.splitter.addWidget(self.graph_spectrum)

        self.main_layout.addWidget(self.splitter)

        # 5. CONSOLE
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #000; color: #0f0; font-family: monospace; font-size: 10px;")
        self.log_console.setMaximumHeight(80)
        self.log_console.setText("--- PRISM V9.1 (Rolling Window 5s) ---")
        self.main_layout.addWidget(self.log_console)

        # VARIABLES
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_audio_tick)
        
        self.current_folder = None
        self.df_global = None
        self.ts_data = None
        self.freq_data_matrix = None # Optimisation V9
        
        self.detected_events = []
        self.current_event_idx = -1
        self.last_hover_ts = 0
        self.min_val_display = 20
        self.res_jour = None
        self.res_nuit = None
        
        self.rta_freqs = ["20Hz", "25Hz", "31.5Hz", "40Hz", "50Hz", "63Hz", "80Hz", "100Hz", "125Hz", "160Hz", "200Hz", "250Hz", "315Hz", "400Hz"]
        self.bg_item = None 
        self.peak_item = None 
        self.avg_item = None 

    def log_message(self, msg):
        self.log_console.append(f"> {msg}")
        log.info(msg)

    # --- CHARGEMENT ---
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier ONYX")
        if folder: self.process_folder(folder)

    def process_folder(self, folder_path):
        self.current_folder = folder_path
        csvs = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        if not csvs: return
        try:
            path = os.path.join(folder_path, csvs[0])
            self.df_global = pd.read_csv(path, sep=';', decimal=',', header=1, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
            self.df_global.columns = self.df_global.columns.str.strip()
            
            # OPTIMISATION V9 : Matrice Numpy pour le calcul temps réel
            cols = self.df_global.columns
            ts_col = next((c for c in cols if 'ts' == c.lower()), None)
            if ts_col:
                self.ts_data = pd.to_numeric(self.df_global[ts_col], errors='coerce').to_numpy()
                
                # On prépare la matrice [Temps x Fréquences]
                freq_list = []
                for f_name in self.rta_freqs:
                    col = next((c for c in cols if f_name.lower() in c.lower()), None)
                    if col:
                        freq_list.append(pd.to_numeric(self.df_global[col], errors='coerce').to_numpy())
                    else:
                        freq_list.append(np.zeros(len(self.df_global)))
                
                # Transposition pour avoir [Lignes, Cols]
                self.freq_data_matrix = np.column_stack(freq_list)

            self.res_jour = None
            self.res_nuit = None
            
            self.update_main_curves()
            self.init_spectrum_graph()
            self.log_message(f"Chargé : {csvs[0]}.")
        except Exception as e: self.log_message(f"Err: {e}")

    # --- TEMPOREL ---
    def update_main_curves(self):
        if self.df_global is None: return
        self.graph_time.clear()
        self.graph_time.addItem(self.playhead)

        cols = self.df_global.columns
        y_col = next((c for c in cols if 'leq' in c.lower() or 'dba' in c.lower()), None)
        if not y_col and len(cols)>2: y_col = cols[2]

        if self.ts_data is not None and y_col:
            y_data = pd.to_numeric(self.df_global[y_col], errors='coerce').to_numpy()
            mask = ~np.isnan(self.ts_data) & ~np.isnan(y_data)
            
            if np.any(mask):
                valid_y = y_data[mask]
                self.min_val_display = np.min(valid_y) if len(valid_y) > 0 else 20
                self.graph_time.plot(self.ts_data[mask], valid_y, pen=pg.mkPen('#00ff00', width=1))
                self.graph_time.setTitle(f"Signal Global : {y_col}")

            for cfg in self.filters_config:
                cb = self.checkboxes[cfg["col_match"]]
                if cb.isChecked():
                    col_name = next((c for c in cols if cfg["col_match"] in c.lower()), None)
                    if col_name:
                        y_freq = pd.to_numeric(self.df_global[col_name], errors='coerce').to_numpy()
                        self.graph_time.plot(self.ts_data[mask], y_freq[mask], pen=pg.mkPen(cfg["color"], width=1))
        
        self.redraw_events()
        self.redraw_thresholds()
        
        if self.ts_data is not None and len(self.ts_data) > 0:
            self.graph_time.getPlotItem().autoRange()

    def redraw_thresholds(self):
        if self.res_jour is not None:
            self.graph_time.addItem(pg.InfiniteLine(pos=self.res_jour, angle=0, pen=pg.mkPen('c', style=Qt.DashLine), label=f"Jour {self.res_jour:.1f}"))
        if self.res_nuit is not None:
            self.graph_time.addItem(pg.InfiniteLine(pos=self.res_nuit, angle=0, pen=pg.mkPen('#00008B', style=Qt.DashLine), label=f"Nuit {self.res_nuit:.1f}"))

    # --- SPECTRE (V9.1 Glissant) ---
    def init_spectrum_graph(self):
        self.graph_spectrum.clear()
        x_ticks = [ (i, f) for i, f in enumerate(self.rta_freqs) ]
        self.graph_spectrum.getPlotItem().getAxis('bottom').setTicks([x_ticks])
        
        # 1. Barres Rouges (Instant)
        self.bg_item = pg.BarGraphItem(x=range(len(self.rta_freqs)), height=[0]*len(self.rta_freqs), width=0.6, brush='r')
        self.graph_spectrum.addItem(self.bg_item)
        
        # Symbole Barre
        h_bar = QPainterPath()
        h_bar.moveTo(-0.4, 0) 
        h_bar.lineTo(0.4, 0)

        # 2. Moyenne 5s (VERT)
        self.avg_item = pg.ScatterPlotItem(x=[], y=[], pen=pg.mkPen('#00FF00', width=3), brush=None, symbol=h_bar, size=1, pxMode=False)
        self.graph_spectrum.addItem(self.avg_item)

        # 3. Crêtes 5s (CYAN)
        self.peak_item = pg.ScatterPlotItem(x=[], y=[], pen=pg.mkPen('c', width=3), brush=None, symbol=h_bar, size=1, pxMode=False)
        self.graph_spectrum.addItem(self.peak_item)
        
        self.update_spectrum_visibility()

    def update_spectrum_visibility(self):
        if self.avg_item: self.avg_item.setVisible(self.cb_rta_avg.isChecked())
        if self.peak_item: self.peak_item.setVisible(self.cb_rta_peak.isChecked())

    def update_spectrum(self, ts):
        if self.freq_data_matrix is None: return
        
        try:
            # 1. Index fin (instant T)
            # searchsorted est très rapide sur des tableaux triés
            idx_end = np.searchsorted(self.ts_data, ts)
            if idx_end >= len(self.ts_data): idx_end = len(self.ts_data) - 1
            
            # 2. Index début (T - 5 secondes)
            ts_start = ts - 5.0
            idx_start = np.searchsorted(self.ts_data, ts_start)
            if idx_start < 0: idx_start = 0
            
            # 3. Extraction fenêtre (Slicing)
            # matrix[lignes, colonnes]
            window = self.freq_data_matrix[idx_start:idx_end+1, :]
            
            # Valeur instantanée (dernière ligne)
            current_vals = window[-1, :] if len(window) > 0 else np.zeros(len(self.rta_freqs))
            
            # CALCULS STATISTIQUES GLISSANTS (V9.1)
            if len(window) > 0:
                avg_vals = np.mean(window, axis=0) # Moyenne verticale
                peak_vals = np.max(window, axis=0) # Max vertical
            else:
                avg_vals = np.zeros(len(self.rta_freqs))
                peak_vals = np.zeros(len(self.rta_freqs))

            # Mise à jour graphique
            if self.bg_item: 
                self.bg_item.setOpts(height=current_vals)
            
            x_range = range(len(self.rta_freqs))
            
            if self.avg_item and self.cb_rta_avg.isChecked():
                self.avg_item.setData(x=x_range, y=avg_vals)
            
            if self.peak_item and self.cb_rta_peak.isChecked():
                self.peak_item.setData(x=x_range, y=peak_vals)

        except Exception as e: pass

    # --- INTERACTION ---
    def on_mouse_move(self, pos):
        mouse_point = self.graph_time.plotItem.vb.mapSceneToView(pos)
        ts = mouse_point.x()
        self.last_hover_ts = ts
        self.update_spectrum(ts)

    def on_audio_tick(self, position_ms):
        if self.last_clicked_ts is None: return
        current_ts = self.audio_start_ts + (position_ms / 1000.0)
        self.playhead.setPos(current_ts)
        self.update_spectrum(current_ts)

    def on_graph_click(self, event):
        if self.df_global is None: return
        try:
            pos = event.scenePos()
            clicked_ts = self.graph_time.plotItem.vb.mapSceneToView(pos).x()
            self.play_audio_at(clicked_ts)
        except: pass

    def play_audio_at(self, ts):
        if self.df_global is None: return
        self.last_clicked_ts = ts
        ts_col = next((c for c in self.df_global.columns if 'ts' == c.lower()), None)
        idx = (self.df_global[ts_col] - ts).abs().idxmin()
        row = self.df_global.iloc[idx]
        
        fname = row.get('Audio_Ref', '')
        if pd.isna(fname): return

        full_path = os.path.join(self.current_folder, str(fname))
        if not os.path.exists(full_path): 
            self.log_message("Audio manquant.")
            return

        file_data = self.df_global[self.df_global['Audio_Ref'] == fname]
        self.audio_start_ts = file_data[ts_col].min()
        offset_ms = int((ts - self.audio_start_ts) * 1000)
        if offset_ms < 0: offset_ms = 0
        
        self.playhead.setPos(ts)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(full_path)))
        self.player.setPosition(offset_ms)
        self.player.play()

    # --- SCAN EXPERT ---
    def run_auto_scan(self):
        if self.df_global is None or not self.ia: return
        self.log_message("⏳ Scan EXPERT...")
        cols = self.df_global.columns
        y_col = next((c for c in cols if 'leq' in c.lower() or 'dba' in c.lower()), None)
        ts_col = next((c for c in cols if 'ts' == c.lower()), None)
        if not y_col: y_col = cols[2]
        t = pd.to_numeric(self.df_global[ts_col], errors='coerce').tolist()
        v = pd.to_numeric(self.df_global[y_col], errors='coerce').tolist()

        (res_j, res_n), points = self.ia.scanner_emergences(t, v)
        self.log_message(f"Résiduels : J {res_j:.1f} | N {res_n:.1f}")

        self.res_jour = res_j
        self.res_nuit = res_n

        self.detected_events = []
        if points:
            zone_start = points[0][0]
            last_ts = points[0][0]
            for i in range(1, len(points)):
                ts = points[i][0]
                if ts - last_ts > 120:
                    self.detected_events.append((zone_start, last_ts))
                    zone_start = ts
                last_ts = ts
            self.detected_events.append((zone_start, last_ts))

        self.log_message(f"Trouvé {len(self.detected_events)} événements.")
        self.redraw_events()
        self.redraw_thresholds()
        self.current_event_idx = -1

    def redraw_events(self):
        for start, end in self.detected_events:
            self.graph_time.plot([start, end], [self.min_val_display, self.min_val_display], pen=pg.mkPen('r', width=3))

    def prev_event(self):
        if self.current_event_idx > 0:
            self.current_event_idx -= 1
            self.jump_to_event()

    def next_event(self):
        if self.current_event_idx < len(self.detected_events) - 1:
            self.current_event_idx += 1
            self.jump_to_event()

    def jump_to_event(self):
        start, end = self.detected_events[self.current_event_idx]
        center = (start + end) / 2
        duration = end - start
        self.graph_time.setXRange(start - 120, end + 120, padding=0)
        self.play_audio_at(center)
        self.log_message(f"Event {self.current_event_idx+1} ({int(duration)}s)")

    def teach_ai(self):
        if not self.ia: return
        d = LearningDialog(self)
        if d.exec_():
            idx = (np.abs(self.ts_data - self.last_clicked_ts)).argmin()
            row = self.df_global.iloc[idx]
            cols_hz = [c for c in self.df_global.columns if 'hz' in c.lower()]
            spectre = {c: float(row[c]) for c in cols_hz if pd.notna(row[c])}
            res = self.ia.save_example(spectre, d.get_label())
            self.log_message(res)
