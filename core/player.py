import sounddevice as sd
import soundfile as sf
import threading
import time

class AudioPlayer:
    """
    Moteur audio optimisé pour les longs fichiers (Streaming SSD -> RAM).
    """
    def __init__(self):
        self.filepath = None
        self.sf_file = None
        self.stream = None
        self.samplerate = 44100
        self.channels = 1
        self.duration = 0.0
        self.is_playing = False
        self.lock = threading.Lock()

    def load(self, filepath):
        self.stop()
        try:
            self.filepath = filepath
            with sf.SoundFile(filepath) as f:
                self.samplerate = f.samplerate
                self.channels = f.channels
                self.duration = float(len(f)) / f.samplerate
            return True, f"Moteur Audio Prêt : {self.duration:.2f}s"
        except Exception as e:
            return False, f"Erreur Audio Load: {e}"

    def play(self, start_time=0.0):
        if not self.filepath: return
        self.stop()

        try:
            self.sf_file = sf.SoundFile(self.filepath)
            frame_pos = int(start_time * self.samplerate)
            if frame_pos < len(self.sf_file):
                self.sf_file.seek(frame_pos)

            def callback(outdata, frames, time_info, status):
                # Si status n'est pas vide, c'est qu'il y a un souci (ex: underflow)
                if status:
                    print(f"[AUDIO WARNING] {status}")
                
                data = self.sf_file.read(frames, always_2d=True, dtype='float32')
                if len(data) < frames:
                    outdata[:len(data)] = data
                    outdata[len(data):] = 0
                    raise sd.CallbackStop
                else:
                    outdata[:] = data

            # --- CORRECTION SON HACHÉ ---
            # On augmente le blocksize (tampon) pour éviter les coupures
            # 16384 frames @ 44.1kHz = ~370ms de tampon. Plus stable.
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                callback=callback,
                blocksize=16384 
            )
            self.stream.start()
            self.is_playing = True

        except Exception as e:
            print(f"[ERREUR PLAYER] {e}")
            self.stop()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.sf_file:
            self.sf_file.close()
            self.sf_file = None
        self.is_playing = False

    def get_time(self):
        if self.sf_file and self.is_playing:
            return self.sf_file.tell() / self.samplerate
        return 0.0
