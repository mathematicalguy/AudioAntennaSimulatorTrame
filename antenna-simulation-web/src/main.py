from antenna_sim import AntennaSimulation
import sys

def main():
    simulation = AntennaSimulation()
    print("Starting Antenna Field Simulation Server...")
    print("Access the visualization at http://localhost:8080")
    
    if '--server' in sys.argv:
        simulation.start(show_server_only=True)
    else:
        simulation.start()

if __name__ == "__main__":
    main()