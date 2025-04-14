import librosa
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

class AudioGraphMaker:
    def __init__(self):
        # Define paths
        self.base_dir = Path(__file__).parent.parent
        self.resources_dir = self.base_dir / 'resources'
        
        # Ensure the resources directory exists
        self.resources_dir.mkdir(exist_ok=True, parents=True)
        print(f"Resources directory ready: {self.resources_dir}")
    
    def create_audio_graph(self, audio_path):
        """Generate visualizations for an audio file and save them in the resources directory"""
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=None)
            filename = Path(audio_path).stem
            
            # Create figure with multiple visualizations
            plt.figure(figsize=(12, 10))
            
            # Plot 1: Waveform
            plt.subplot(3, 1, 1)
            plt.title('Waveform')
            librosa.display.waveshow(y, sr=sr)
            plt.tight_layout()
            
            # Plot 2: Spectrogram
            plt.subplot(3, 1, 2)
            plt.title('Spectrogram')
            D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
            librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='hz')
            plt.colorbar(format='%+2.0f dB')
            plt.tight_layout()
            
            # Plot 3: Mel Spectrogram
            plt.subplot(3, 1, 3)
            plt.title('Mel Spectrogram')
            S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
            S_dB = librosa.power_to_db(S, ref=np.max)
            librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel')
            plt.colorbar(format='%+2.0f dB')
            plt.tight_layout()
            
            # Save the figure
            output_path = self.resources_dir / f"{filename}_graphs.png"
            plt.savefig(output_path)
            plt.close()
            
            print(f"Created audio graph for {filename} at {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error creating audio graph for {audio_path}: {str(e)}")
            return None


# Helper function to generate graph from an audio file
def generate_graph_for_audio(audio_file_path):
    maker = AudioGraphMaker()
    return maker.create_audio_graph(audio_file_path)