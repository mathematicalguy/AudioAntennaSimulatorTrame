import numpy as np
import pyvista as pv
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify, html
from audio_file_upload import AudioUploaderComponent

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

        # Simulation Parameters
        self.antenna_length = 1.0
        self.antenna_radius = 0.02
        self.current_amplitude = 1.0
        self.min_current = 0.1
        self.max_current = 3.0
        self.frequency = 1.0
        self.freq_unit = 'Hz'
        self.antenna_type = 'Dipole'
        self.freq_multipliers = {
            'Hz': 1,
            'kHz': 1e3,
            'MHz': 1e6,
            'GHz': 1e9
        }
        self.antenna_types = [
            'Dipole',
            'Monopole',
            'Loop',
            'Yagi'
        ]
        self.time_step = 0.05
        self.t = 0.0

        # Initialize simulation components
        self.field_points = self.generate_field_points()
        self.vectors = np.zeros_like(self.field_points)
        self.field_data = pv.PolyData(self.field_points)
        self.field_data["E"] = self.vectors

        # Initialize audio uploader
        self.audio_uploader = AudioUploaderComponent(self.server)

        # Setup plotter
        self.setup_plotter()
        self.setup_ui()
        self.setup_controllers()

    def generate_field_points(self):
        phi = np.linspace(0, 2*np.pi, 30)
        theta = np.linspace(0, np.pi, 15)
        r = np.linspace(0.2, 2.0, 10)
        points = []
        for ri in r:
            for ti in theta:
                for pi in phi:
                    x = ri * np.sin(ti) * np.cos(pi)
                    y = ri * np.sin(ti) * np.sin(pi)
                    z = ri * np.cos(ti)
                    points.append([x, y, z])
        return np.array(points)

    def make_antenna(self, length):
        if self.state.antenna_type == 'Dipole':
            return self._make_dipole(length)
        elif self.state.antenna_type == 'Monopole':
            return self._make_monopole(length)
        elif self.state.antenna_type == 'Loop':
            return self._make_loop(length)
        elif self.state.antenna_type == 'Yagi':
            return self._make_yagi(length)
        return self._make_dipole(length)  # default to dipole

    def _make_dipole(self, length):
        body = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=self.antenna_radius, height=length)
        base = pv.Cylinder(center=(0, 0, -length/20), direction=(0, 0, 1), radius=self.antenna_radius*3, height=length/10)
        top = pv.Sphere(center=(0, 0, length), radius=self.antenna_radius*1.5)
        return body + base + top

    def _make_monopole(self, length):
        body = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=self.antenna_radius, height=length/2)
        base = pv.Cylinder(center=(0, 0, -length/20), direction=(0, 0, 1), radius=length/8, height=length/10)
        top = pv.Sphere(center=(0, 0, length/2), radius=self.antenna_radius*1.5)
        ground = pv.Disc(center=(0, 0, -length/20), normal=(0, 0, 1), radius=length/4)
        return body + base + top + ground

    def _make_loop(self, length):
        radius = length / (2 * np.pi)
        ring = pv.Circle(radius=radius, resolution=100)
        tube = ring.tube(radius=self.antenna_radius)
        base = pv.Cylinder(center=(0, 0, -length/20), direction=(0, 0, 1), radius=self.antenna_radius*3, height=length/10)
        return tube + base

    def _make_yagi(self, length):
        # Create main dipole
        main_element = self._make_dipole(length)
        
        # Add director elements (shorter)
        director1 = self._make_dipole(length * 0.8)
        director1.translate((0, length/2, length/4))
        
        director2 = self._make_dipole(length * 0.7)
        director2.translate((0, length, length/2))
        
        # Add reflector element (longer)
        reflector = self._make_dipole(length * 1.2)
        reflector.translate((0, -length/2, -length/4))
        
        return main_element + director1 + director2 + reflector

    def setup_plotter(self):
        self.plotter = pv.Plotter(off_screen=True)
        self.plotter.set_background("black")
        self.plotter.background_color = "black"
        self.plotter.renderer.SetBackground(0, 0, 0)
        
        # Add the antenna first to set bounds
        self.antenna_actor = self.plotter.add_mesh(self.make_antenna(self.antenna_length), color="silver", name="antenna")
        
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

    def get_actual_frequency(self):
        """Convert the frequency value based on the selected unit"""
        return self.state.frequency * self.freq_multipliers[self.state.freq_unit]

    def update_scene(self, **kwargs):
        self.t += self.time_step
        self.plotter.remove_actor("antenna")
        self.plotter.add_mesh(self.make_antenna(self.state.antenna_length), color="silver", name="antenna")
        
        distances = np.linalg.norm(self.field_points, axis=1)
        actual_freq = self.get_actual_frequency()
        phase = 2 * np.pi * (actual_freq * self.t - distances / 2)
        
        # Calculate current amplitude based on min and max current
        current_range = self.state.max_current - self.state.min_current
        current = self.state.min_current + (current_range * abs(np.sin(2 * np.pi * actual_freq * self.t)))
        
        self.vectors[:, 0] = current * np.sin(phase) * self.field_points[:, 0] / distances
        self.vectors[:, 1] = current * np.sin(phase) * self.field_points[:, 1] / distances
        self.vectors[:, 2] = current * np.cos(phase) * np.cos(np.arctan2(distances, self.field_points[:, 2]))

        intensities = np.linalg.norm(self.vectors, axis=1)
        self.field_data["E"] = self.vectors
        self.field_data["intensity"] = intensities
        glyphs = self.field_data.glyph(orient="E", scale="intensity", factor=0.1)
        
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
                                v_model=("antenna_type", self.antenna_type),
                                items=self.antenna_types,
                                label="Antenna Type",
                                on_change=self.update_scene,
                                hide_details=True,
                            )
                    
                    # Frequency controls with unit selection
                    with vuetify.VRow(classes="mb-4"):
                        with vuetify.VCol(cols=8):
                            vuetify.VSlider(
                                v_model=("frequency", self.frequency),
                                min=1,
                                max=1000,
                                step=1,
                                label="Frequency",
                                thumb_label="always",
                                on_input=self.update_scene,
                            )
                        with vuetify.VCol(cols=4):
                            vuetify.VSelect(
                                v_model=("freq_unit", self.freq_unit),
                                items=list(self.freq_multipliers.keys()),
                                label="Unit",
                                on_change=self.update_scene,
                                hide_details=True,
                            )
                    
                    vuetify.VSlider(
                        v_model=("max_current", self.max_current),
                        min=0.1,
                        max=5.0,
                        step=0.1,
                        label="Maximum Current (A)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
                    )
                    
                    vuetify.VSlider(
                        v_model=("min_current", self.min_current),
                        min=0.05,
                        max=2.0,
                        step=0.05,
                        label="Minimum Current (A)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
                    )
                    
                    vuetify.VSlider(
                        v_model=("antenna_length", self.antenna_length),
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
        self.state.antenna_length = self.antenna_length
        self.state.min_current = self.min_current
        self.state.max_current = self.max_current
        self.state.frequency = self.frequency
        self.state.freq_unit = self.freq_unit

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