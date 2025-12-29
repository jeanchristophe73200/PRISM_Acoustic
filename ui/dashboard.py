import os
import shutil
import pandas as pd
import numpy as np
import re
import pyqtgraph as pg
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                             QLabel, QMessageBox, QTextEdit, QInputDialog, QComboBox, QDialog, 
                             QMenu, QAction, QSplitter, QCheckBox)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QPainterPath, QColor, QCursor, QFont
from utils.logger import log

def h_bar_path():
    p = QPainterPath()
    p.moveTo(-0.4, 0)
    p.lineTo(0.4, 0)
    return p

# --- Fenêtre de Qualification ---
class LearningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRISM - Qualification")
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Identifier la source sonore :")
        self.layout.addWidget(self.label)
        self.combo = QComboBox()
        self.combo.addItems(["Source + (PAC)", "Source Std", "Source -", "Résiduel (Calme)", "Autre (Exclusion)"])
        self.layout.addWidget(self.combo)
        self.btn_ok = QPushButton("Valider & Sauvegarder")
        self.btn_ok.clicked.connect(self.accept)
        self.layout.addWidget(self.btn_ok)
    def get_label(self): return self.combo.currentText()

# --- Etiquette Graphique ---
class ClickableTextItem(pg.TextItem):
    def __init__(self, text, ts_val, parent_dashboard, color_hex, **kwargs):
        super().__init__(text=text, **kwargs)
        self.ts_val = ts_val
        self.dash = parent_dashboard
        self.setColor(QColor(255, 255, 255)) 
        self.setFont(QFont("Arial", 11, QFont.Bold))
        self.fill = pg.mkBrush(color_hex)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        # Z=20 : Toujours tout devant pour être lisible
        self.setZValue(20) 
    
    def mouseClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.dash.open_marker_menu(self.ts_val, ev.screenPos())

# --- DASHBOARD V10.2 (Gestion des Calques Graphiques) ---
class Dashboard(QWidget):
    def __init__(self, ia_interface=None):
        super().__init__()
        self.ia = ia_interface 
        self.main_layout = QVBoxLayout(self)
        self.setFocusPolicy(Qt.StrongFocus)

        # 1. BARRE D'OUTILS
        self.toolbar_layout = QHBoxLayout()
        btn_style = "padding: 6px; font-size: 12px; border-radius: 4px; color: white; font-weight: bold;"
        
        self.btn_load = QPushButton("📂 CHARGER DOSSIER")
        self.btn_load.setStyleSheet(btn_style + "background-color: #444;")
        self.btn_load.clicked.connect(self.select_folder)
        self.toolbar_layout.addWidget(self.btn_load)

        self.toolbar_layout.addStretch()
        self.main_layout.addLayout(self.toolbar_layout)

        # 2. FILTRES
        self.filter_layout = QHBoxLayout()
        self.lbl_filtres = QLabel("Superposition :")
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

        # 3. VISUALISATION
        self.splitter = QSplitter(Qt.Vertical)
        
        # A. Graphique Temporel
        pg.setConfigOption('background', '#1e1e1e')
        self.graph_time = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.graph_time.showGrid(x=True, y=True, alpha=0.3)
        self.graph_time.setLabel('left', 'Niveau (dB)')
        
        # Tête de lecture (Z=100 : Toujours visible)
        self.playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('r', width=1))
        self.playhead.setZValue(100)
        self.graph_time.addItem(self.playhead)
        
        self.graph_time.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.graph_time.scene().sigMouseClicked.connect(self.on_graph_click)
        self.splitter.addWidget(self.graph_time)

        # B. Graphique Spectre
        self.graph_spectrum = pg.PlotWidget()
        self.graph_spectrum.setLabel('bottom', 'Fréquence (Hz)')
        self.graph_spectrum.setLabel('left', 'dB')
        self.graph_spectrum.showGrid(x=True, y=True, alpha=0.5)
        self.graph_spectrum.setYRange(0, 90)
        self.splitter.addWidget(self.graph_spectrum)

        self.main_layout.addWidget(self.splitter)

        # 4. CONSOLE
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #000; color: #0f0; font-family: monospace; font-size: 10px;")
        self.log_console.setMaximumHeight(60)
        self.log_console.setText("--- PRISM V10.2 (Fix Z-Order) ---")
        self.main_layout.addWidget(self.log_console)

        # VARIABLES
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.on_audio_tick)
        
        self.current_folder = None
        self.current_csv_path = None
        self.df_global = None
        self.ts_data = None
        self.freq_data_matrix = None
        self.metadata_header = "" 
        self.onyx_markers = [] 
        self.marker_items = [] 
        self.last_hover_ts = 0
        self.min_val_display = 20
        self.max_val_display = 100 
        self.temp_start_ts = None
        self.temp_line_item = None
        self.rta_freqs = ["20Hz", "25Hz", "31.5Hz", "40Hz", "50Hz", "63Hz", "80Hz", "100Hz", "125Hz", "160Hz", "200Hz", "250Hz", "315Hz", "400Hz"]
        self.bg_item = None 
        
        self.init_spectrum_graph()

    def log_message(self, msg):
        self.log_console.append(f"> {msg}")
        log.info(msg)

    # --- CLAVIER ---
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
            else:
                self.player.play()
        elif event.key() == Qt.Key_Right:
            pos = self.player.position() + 60000
            self.player.setPosition(pos)
        elif event.key() == Qt.Key_Left:
            pos = self.player.position() - 60000
            if pos < 0: pos = 0
            self.player.setPosition(pos)
        else:
            super().keyPressEvent(event)

    # --- CHARGEMENT ---
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner Dossier ONYX")
        if folder: self.process_folder(folder)

    def process_folder(self, folder_path):
        self.current_folder = folder_path
        all_csvs = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        data_csvs = [f for f in all_csvs if "knowledge" not in f.lower()]
        if not data_csvs: return

        prism_file = next((f for f in data_csvs if "_PRISM" in f), None)
        original_file = next((f for f in data_csvs if "_PRISM" not in f), None)
        
        target_file = None
        if prism_file:
            self.log_message(f"Reprise : {prism_file}")
            target_file = prism_file
        elif original_file:
            self.log_message(f"Nouveau projet depuis : {original_file}")
            src = os.path.join(folder_path, original_file)
            base_name = original_file.replace(".csv", "")
            new_name = f"{base_name}_PRISM.csv"
            dst = os.path.join(folder_path, new_name)
            try:
                shutil.copy2(src, dst)
                target_file = new_name
            except Exception as e:
                self.log_message(f"Err copie : {e}")
                target_file = original_file 
        
        if target_file:
            self.current_csv_path = os.path.join(folder_path, target_file)
            self._internal_load()

    def _internal_load(self):
        try:
            header_row = 0
            self.metadata_header = ""
            with open(self.current_csv_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()
                if first_line.startswith('#'):
                    self.metadata_header = first_line
                    header_row = 1 
                else:
                    header_row = 0

            self.df_global = pd.read_csv(self.current_csv_path, sep=';', decimal=',', header=header_row, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
            self.df_global.columns = self.df_global.columns.str.strip()
            
            cols = self.df_global.columns
            ts_col = next((c for c in cols if 'ts' == c.lower()), None)
            
            self.onyx_markers = []
            note_col = next((c for c in cols if 'note' in c.lower()), None)
            if ts_col and note_col:
                mask_notes = self.df_global[note_col].notna()
                if mask_notes.any():
                    markers_df = self.df_global[mask_notes]
                    t_notes = markers_df[ts_col].tolist()
                    l_notes = markers_df[note_col].astype(str).tolist()
                    self.onyx_markers = list(zip(t_notes, l_notes))
                    # Nettoyage des doublons exacts
                    self.onyx_markers = list(set(self.onyx_markers))
                    self.onyx_markers.sort(key=lambda x: x[0])
                    self.log_message(f"Zones chargées : {len(self.onyx_markers)}")

            if ts_col:
                self.ts_data = pd.to_numeric(self.df_global[ts_col], errors='coerce').to_numpy()
                freq_list = []
                for f_name in self.rta_freqs:
                    col = next((c for c in cols if f_name.lower() in c.lower()), None)
                    if col:
                        freq_list.append(pd.to_numeric(self.df_global[col], errors='coerce').to_numpy())
                    else:
                        freq_list.append(np.zeros(len(self.df_global)))
                self.freq_data_matrix = np.column_stack(freq_list)

            self.update_main_curves()
        except Exception as e: self.log_message(f"Err Load: {e}")

    def save_changes_to_disk(self):
        if self.df_global is None or not self.current_csv_path: return
        try:
            with open(self.current_csv_path, 'w', encoding='utf-8-sig') as f:
                if self.metadata_header: f.write(self.metadata_header)
                self.df_global.to_csv(f, sep=';', decimal=',', index=False)
            self.log_message("Sauvegardé.")
        except Exception as e:
            self.log_message(f"Err Save : {e}")

    def update_main_curves(self):
        if self.df_global is None: return
        self.graph_time.clear()
        self.marker_items = [] 
        self.graph_time.addItem(self.playhead)

        cols = self.df_global.columns
        y_col = next((c for c in cols if 'leq' in c.lower() or 'dba' in c.lower()), None)
        if not y_col and len(cols)>2: y_col = cols[2]

        if self.ts_data is not None and y_col:
            y_data = pd.to_numeric(self.df_global[y_col], errors='coerce').to_numpy()
            mask = ~np.isnan(self.ts_data) & ~np.isnan(y_data)
            
            if np.any(mask):
                valid_y = y_data[mask]
                self.min_val_display = np.min(valid_y)
                self.max_val_display = np.max(valid_y)
                
                # COURBE VERTE : Z=10 (DEVANT LES ZONES)
                curve = self.graph_time.plot(self.ts_data[mask], valid_y, pen=pg.mkPen('#00ff00', width=1))
                curve.setZValue(10)
                
                self.graph_time.setTitle(f"Signal Global : {y_col}")

            for cfg in self.filters_config:
                cb = self.checkboxes[cfg["col_match"]]
                if cb.isChecked():
                    col_name = next((c for c in cols if cfg["col_match"] in c.lower()), None)
                    if col_name:
                        y_freq = pd.to_numeric(self.df_global[col_name], errors='coerce').to_numpy()
                        c_filt = self.graph_time.plot(self.ts_data[mask], y_freq[mask], pen=pg.mkPen(cfg["color"], width=1))
                        c_filt.setZValue(10)
        
        self.redraw_markers()
        if self.ts_data is not None and len(self.ts_data) > 0:
            self.graph_time.getPlotItem().autoRange()

    def get_marker_color(self, label):
        lbl = label.lower()
        if "source +" in lbl: return '#FF0000'
        if "source std" in lbl: return '#FF8C00'
        if "source -" in lbl: return '#FFD700'
        if "résiduel" in lbl: return '#00FF00'
        if "autre" in lbl or "exclusion" in lbl: return '#808080'
        return '#AAAAAA'

    def redraw_markers(self):
        for i, (ts, full_label) in enumerate(self.onyx_markers):
            label_clean = full_label.split('{')[0].strip()
            duration = 120.0 
            match = re.search(r'\{d=([0-9\.]+)\}', full_label)
            if match: duration = float(match.group(1))
            
            color_hex = self.get_marker_color(label_clean)
            
            half = duration / 2.0
            region = pg.LinearRegionItem(values=[ts-half, ts+half], orientation=pg.LinearRegionItem.Vertical)
            c = QColor(color_hex)
            c.setAlpha(60) # Opacité réduite (23%)
            region.setBrush(c)
            for l in region.lines: l.setPen(pg.mkPen(color_hex))
            region.setMovable(False)
            
            # ZONES : Z=-10 (ARRIÈRE PLAN)
            region.setZValue(-10)
            
            self.graph_time.addItem(region)
            
            t_item = ClickableTextItem(
                text=label_clean, ts_val=ts, parent_dashboard=self, color_hex=color_hex, anchor=(0.5, 1)
            )
            y_pos = self.max_val_display + (self.max_val_display - self.min_val_display) * 0.1 * (1 + (i % 3))
            t_item.setPos(ts, y_pos)
            self.graph_time.addItem(t_item)
            self.marker_items.append(region)
            self.marker_items.append(t_item)

    # --- MENU CONTEXTUEL ---
    def open_marker_menu(self, ts, screen_pos):
        qpoint = screen_pos.toPoint()
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #FFF; color: #000; } QMenu::item:selected { background-color: #007AFF; color: white; }")

        current = next(((t, l) for t, l in self.onyx_markers if t == ts), None)
        lbl_clean = current[1].split('{')[0].strip() if current else "??"
        
        menu.addAction(f"Éditer : {lbl_clean}").setEnabled(False)
        menu.addSeparator()
        menu.addAction("❌ Supprimer").triggered.connect(lambda: self.modify_marker(ts, "DELETE"))
        menu.addSeparator()
        
        types = ["Source + (PAC)", "Source Std", "Source -", "Résiduel (Calme)", "Autre (Exclusion)"]
        for t in types:
            if t not in lbl_clean:
                menu.addAction(f"Changer en : {t}").triggered.connect(lambda c, new_l=t: self.modify_marker(ts, new_l))
        menu.exec_(qpoint)

    def modify_marker(self, ts, action):
        if action == "DELETE":
            self.onyx_markers = [m for m in self.onyx_markers if m[0] != ts]
            new_note = np.nan
            self.log_message("Zone supprimée.")
        else:
            old_note = next((l for t, l in self.onyx_markers if t == ts), "")
            duration_part = " {d=120}" 
            match = re.search(r'\{d=([0-9\.]+)\}', old_note)
            if match: duration_part = f" {{d={match.group(1)}}}"
            
            new_note = f"{action}{duration_part}"
            self.onyx_markers = [(t, new_note) if t == ts else (t, l) for t, l in self.onyx_markers]
            self.log_message(f"Modifié : {action}")
        
        if self.ts_data is not None:
            idx = (np.abs(self.ts_data - ts)).argmin()
            self.df_global.loc[idx, 'note'] = new_note
            self.save_changes_to_disk()
        self.update_main_curves()

    def init_spectrum_graph(self):
        self.graph_spectrum.clear()
        x_ticks = [ (i, f) for i, f in enumerate(self.rta_freqs) ]
        self.graph_spectrum.getPlotItem().getAxis('bottom').setTicks([x_ticks])
        self.bg_item = pg.BarGraphItem(x=range(len(self.rta_freqs)), height=[0]*len(self.rta_freqs), width=0.6, brush='r')
        self.graph_spectrum.addItem(self.bg_item)

    def update_spectrum(self, ts):
        if self.freq_data_matrix is None: return
        try:
            idx = np.searchsorted(self.ts_data, ts)
            if idx >= len(self.ts_data): idx = len(self.ts_data)-1
            if idx < 0: idx = 0
            start = max(0, idx-1)
            window = self.freq_data_matrix[start:idx+1, :]
            if len(window) > 0:
                vals = window[-1, :]
                self.bg_item.setOpts(height=vals)
        except: pass

    def on_mouse_move(self, pos):
        mouse_point = self.graph_time.plotItem.vb.mapSceneToView(pos)
        self.last_hover_ts = mouse_point.x()
        self.update_spectrum(self.last_hover_ts)

    def on_audio_tick(self, position_ms):
        if self.player.state() != QMediaPlayer.PlayingState: return
        if self.last_clicked_ts is None: return
        current_ts = self.audio_start_ts + (position_ms / 1000.0)
        self.playhead.setPos(current_ts)
        self.update_spectrum(current_ts)
        view_x = self.graph_time.viewRange()[0]
        if current_ts < view_x[0] or current_ts > view_x[1]:
            span = view_x[1] - view_x[0]
            self.graph_time.setXRange(current_ts - span/2, current_ts + span/2, padding=0)

    def on_graph_click(self, event):
        if self.df_global is None: return
        try:
            pos = event.scenePos()
            clicked_ts = self.graph_time.plotItem.vb.mapSceneToView(pos).x()

            if event.modifiers() == Qt.ShiftModifier:
                if self.temp_start_ts is None:
                    self.temp_start_ts = clicked_ts
                    self.temp_line_item = pg.InfiniteLine(pos=clicked_ts, angle=90, pen=pg.mkPen('w', width=2, style=Qt.DotLine), movable=False)
                    self.graph_time.addItem(self.temp_line_item)
                    self.log_message("🚩 Début défini. Maj+Clic pour Fin.")
                else:
                    raw_start, raw_end = min(self.temp_start_ts, clicked_ts), max(self.temp_start_ts, clicked_ts)
                    idx_s = (np.abs(self.ts_data - raw_start)).argmin()
                    idx_e = (np.abs(self.ts_data - raw_end)).argmin()
                    real_s, real_e = self.ts_data[idx_s], self.ts_data[idx_e]
                    
                    if real_s == real_e:
                        self.log_message("⚠️ Trop court.")
                        return

                    dur = real_e - real_s
                    center = (real_s + real_e) / 2
                    
                    if self.temp_line_item: self.graph_time.removeItem(self.temp_line_item)
                    self.temp_start_ts = None
                    self.temp_line_item = None

                    d = LearningDialog(self)
                    if d.exec_():
                        lbl = d.get_label()
                        nt = f"{lbl} {{d={dur:.1f}}}"
                        idx_c = (np.abs(self.ts_data - center)).argmin()
                        real_c = self.ts_data[idx_c]
                        self.df_global.loc[idx_c, 'note'] = nt
                        self.save_changes_to_disk()
                        self.onyx_markers.append((real_c, nt))
                        self.redraw_markers()
                        self.log_message(f"➕ Zone : {lbl}")
                    else:
                        self.log_message("Annulé.")
            else:
                if self.temp_start_ts:
                    if self.temp_line_item: self.graph_time.removeItem(self.temp_line_item)
                    self.temp_start_ts = None
                    self.temp_line_item = None
                    self.log_message("Création annulée.")
                self.play_audio_at(clicked_ts)
                self.setFocus()
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
             self.log_message(f"Audio introuvable.")
             return

        file_data = self.df_global[self.df_global['Audio_Ref'] == fname]
        self.audio_start_ts = file_data[ts_col].min()
        offset_ms = int((ts - self.audio_start_ts) * 1000)
        if offset_ms < 0: offset_ms = 0
        self.playhead.setPos(ts)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(full_path)))
        self.player.setPosition(offset_ms)
        self.player.play()
        self.setFocus()
