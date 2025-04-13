from antenna_sim import AntennaSimulation
from audio_file_upload import AudioUploaderComponent
import sys

class MainApplication:
    def __init__(self):
        self.simulation = AntennaSimulation()
        
        # Initialize the audio uploader component
        self.audio_uploader = AudioUploaderComponent(self.simulation.server)
        
    def setup_ui(self):
        with SinglePageWithDrawerLayout(self.simulation.server) as layout:
            # Add the upload widget wherever you want it in your layout
            layout.content.add(self.audio_uploader.get_upload_widget())
            
def main():
    app = MainApplication()
    print("Starting Antenna Field Simulation Server...")
    print("Access the visualization at http://localhost:8080")
    
    if '--server' in sys.argv:
        app.simulation.start(show_server_only=True)
    else:
        app.simulation.start()

if __name__ == "__main__":
    main()