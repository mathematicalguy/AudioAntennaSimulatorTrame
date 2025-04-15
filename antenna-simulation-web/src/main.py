from antenna_display import AntennaSimulation
from trame.ui.vuetify import SinglePageWithDrawerLayout
import sys

class MainApplication:
    def __init__(self):
        self.simulation = AntennaSimulation()
        
    def setup_ui(self):
        with SinglePageWithDrawerLayout(self.simulation.server) as layout:
            # The audio uploader is already integrated in the AntennaSimulation class
            pass
            
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