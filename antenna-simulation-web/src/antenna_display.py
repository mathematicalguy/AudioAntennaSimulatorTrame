import numpy as np
import pyvista as pv
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify, html
from audio_file_upload import AudioUploaderComponent
from antenna_simulator import AntennaSimulator

class AntennaSimulation:
    def __init__(self):
        # Initialize server
        self.server = get_server(
            host="localhost", 
            port=8080, 
            client_type='vue2',
            allow_multi_clients=True
        )
        self.state, self.ctrl = self.server.state, self.server.controller

        # Create simulator instance
        self.simulator = AntennaSimulator()
        
        # Initialize audio uploader
        self.audio_uploader = AudioUploaderComponent(self.server)

        # Setup plotter
        self.setup_plotter()
        self.setup_ui()
        self.setup_controllers()

    def setup_plotter(self):
        self.plotter = pv.Plotter(off_screen=True)
        self.plotter.set_background("black")
        self.plotter.background_color = "black"
        self.plotter.renderer.SetBackground(0, 0, 0)
        
        # Add the antenna first to set bounds
        self.antenna_actor = self.plotter.add_mesh(self.simulator.antenna_mesh, color="silver", name="antenna")
        
        # Get bounds of the scene and set camera based on scene size
        bounds = self.plotter.renderer.ComputeVisiblePropBounds()
        diagonal = np.sqrt(np.sum((np.array(bounds[1::2]) - np.array(bounds[::2])) ** 2))
        
        # Set camera position and parameters
        camera = self.plotter.renderer.GetActiveCamera()
        camera.SetPosition(diagonal, diagonal, diagonal)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 0, 1)
        
        # Set clipping range to constrain zoom
        near_clip = diagonal * 0.1
        far_clip = diagonal * 3.0
        camera.SetClippingRange(near_clip, far_clip)
        
        # Set initial view angle
        camera.Elevation(20)
        camera.Azimuth(45)
        camera.Zoom(1.2)
        
        # Reset the camera to apply settings
        self.plotter.renderer.ResetCameraClippingRange()
        self.plotter.reset_camera()

    def update_scene(self, **kwargs):
        # Update simulator parameters
        params = {
            'antenna_length': self.state.antenna_length,
            'min_current': self.state.min_current,
            'max_current': self.state.max_current,
            'frequency': self.state.frequency,
            'freq_unit': self.state.freq_unit,
            'antenna_type': self.state.antenna_type
        }
        
        # Run simulation update
        sim_results = self.simulator.update_simulation(**params)
        
        # Update visualization
        self.plotter.remove_actor("antenna")
        self.plotter.add_mesh(sim_results['antenna_mesh'], color="silver", name="antenna")
        
        glyphs = sim_results['field_data'].glyph(orient="E", scale="intensity", factor=0.1)
        
        self.plotter.remove_actor("field")
        self.plotter.add_mesh(glyphs, scalars="intensity", cmap="plasma", name="field", opacity=0.8)
        
        if self.plotter.ren_win:
            self.plotter.render()
            self.plotter.ren_win.Modified()
            self.plotter.ren_win.Render()

    def setup_controllers(self):
        self.ctrl.on_server_ready.add(self.update_scene)

        @self.state.change("server_ready")
        def on_ready(ready=False, **kwargs):
            if ready:
                self.update_scene()
                self.ctrl.tick_period = 50
                self.ctrl.tick = True
        
        @self.state.change("uploaded_file")
        def on_file_uploaded(uploaded_file=None, **kwargs):
            if uploaded_file:
                print(f"Processing audio file: {uploaded_file}")
                self.process_audio_file(uploaded_file)

        @self.ctrl.trigger("tick")
        def on_tick():
            if self.ctrl.tick:
                self.update_scene()
    
    def process_audio_file(self, file_path):
        """Process the uploaded audio file and update simulation parameters"""
        try:
            import librosa
            import numpy as np
            
            # Load the audio file
            y, sr = librosa.load(file_path, sr=None)
            
            # Extract frequency information
            D = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            times = librosa.times_like(D, sr=sr)
            
            # Find dominant frequency
            dominant_freq_index = np.argmax(np.mean(D, axis=1))
            dominant_freq = freqs[dominant_freq_index]
            
            # Scale to reasonable range for visualization
            scaled_freq = min(1000, max(1, dominant_freq / 100))
            
            # Update simulation parameters based on audio
            self.state.frequency = scaled_freq
            
            # Set appropriate frequency unit
            if scaled_freq < 1:
                self.state.freq_unit = 'Hz'
            elif scaled_freq < 1000:
                self.state.freq_unit = 'Hz'
            else:
                self.state.freq_unit = 'kHz'
                self.state.frequency = scaled_freq / 1000
                
            # Store audio data for possible animation
            self.audio_data = y
            self.audio_sr = sr
            
            print(f"Audio processed: Dominant frequency = {dominant_freq} Hz")
            
        except Exception as e:
            print(f"Error processing audio file: {str(e)}")
            self.state.upload_status = f"Error processing audio: {str(e)}"

    def setup_ui(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("Antenna Field Simulation")
            
            # Create a navigation drawer for parameters
            with vuetify.VNavigationDrawer(
                v_model=("nav_drawer", True),
                app=True,
                clipped=True,
                width=350,
            ):
                with vuetify.VContainer(
                    classes="pa-4",
                ):
                    html.Div("Simulation Parameters", classes="text-h6 mb-4")
                    
                    # Antenna Type Selection
                    with vuetify.VRow(classes="mb-4"):
                        with vuetify.VCol(cols=12):
                            vuetify.VSelect(
                                v_model=("antenna_type", self.simulator.antenna_type),
                                items=self.simulator.antenna_types,
                                label="Antenna Type",
                                on_change=self.update_scene,
                                hide_details=True,
                            )
                    
                    # Frequency controls with unit selection
                    with vuetify.VRow(classes="mb-4"):
                        with vuetify.VCol(cols=8):
                            vuetify.VSlider(
                                v_model=("frequency", self.simulator.frequency),
                                min=1,
                                max=1000,
                                step=1,
                                label="Frequency",
                                thumb_label="always",
                                on_input=self.update_scene,
                            )
                        with vuetify.VCol(cols=4):
                            vuetify.VSelect(
                                v_model=("freq_unit", self.simulator.freq_unit),
                                items=list(self.simulator.freq_multipliers.keys()),
                                label="Unit",
                                on_change=self.update_scene,
                                hide_details=True,
                            )
                    
                    vuetify.VSlider(
                        v_model=("max_current", self.simulator.max_current),
                        min=0.1,
                        max=5.0,
                        step=0.1,
                        label="Maximum Current (A)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
                    )
                    
                    vuetify.VSlider(
                        v_model=("min_current", self.simulator.min_current),
                        min=0.05,
                        max=2.0,
                        step=0.05,
                        label="Minimum Current (A)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
                    )
                    
                    vuetify.VSlider(
                        v_model=("antenna_length", self.simulator.antenna_length),
                        min=0.2,
                        max=2.0,
                        step=0.05,
                        label="Antenna Length (m)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
                    )

                    # Add divider before audio upload section
                    vuetify.VDivider(classes="mb-4")
                    
                    # Include audio uploader component directly in the layout
                    with self.audio_uploader.get_upload_widget():
                        pass

            # Main content area
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
                    vtk.VtkRemoteView(
                        self.plotter.ren_win,
                        ref="view",
                        camera_parallel_projection=False,
                        interactor_settings={
                            "max_distance": 1.0,  # Reduced max zoom out distance
                            "min_distance": 0.5,  # Increased min zoom in distance
                            "interaction": 2,     # Disable camera movement
                            "prevent_wheel": True, # Prevent zooming
                            "prevent_pan": True,   # Prevent panning
                            "prevent_rotation": True  # Prevent rotation
                        }
                    )

    def initialize_state(self):
        self.state.antenna_length = self.simulator.antenna_length
        self.state.min_current = self.simulator.min_current
        self.state.max_current = self.simulator.max_current
        self.state.frequency = self.simulator.frequency
        self.state.freq_unit = self.simulator.freq_unit

    def start(self, show_server_only=False):
        try:
            self.initialize_state()
            self.server.start(show_server_only=show_server_only)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Please ensure all dependencies are installed correctly")

if __name__ == "__main__":
    import sys
    simulation = AntennaSimulation()
    print("Starting Antenna Field Simulation Server...")
    print("Access the visualization at http://localhost:8080")
    
    if '--server' in sys.argv:
        simulation.start(show_server_only=True)
    else:
        simulation.start()