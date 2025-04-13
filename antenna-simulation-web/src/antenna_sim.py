import numpy as np
import pyvista as pv
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify, html

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
        self.time_step = 0.05
        self.t = 0.0

        # Initialize simulation components
        self.field_points = self.generate_field_points()
        self.vectors = np.zeros_like(self.field_points)
        self.field_data = pv.PolyData(self.field_points)
        self.field_data["E"] = self.vectors

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
        body = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=self.antenna_radius, height=length)
        base = pv.Cylinder(center=(0, 0, -length/20), direction=(0, 0, 1), radius=self.antenna_radius*3, height=length/10)
        top = pv.Sphere(center=(0, 0, length), radius=self.antenna_radius*1.5)
        return body + base + top

    def setup_plotter(self):
        self.plotter = pv.Plotter(off_screen=True)
        self.plotter.set_background("black")
        self.plotter.background_color = "black"
        self.plotter.renderer.SetBackground(0, 0, 0)
        self.antenna_actor = self.plotter.add_mesh(self.make_antenna(self.antenna_length), color="silver", name="antenna")

    def update_scene(self, **kwargs):
        self.t += self.time_step
        self.plotter.remove_actor("antenna")
        self.plotter.add_mesh(self.make_antenna(self.state.antenna_length), color="silver", name="antenna")
        
        distances = np.linalg.norm(self.field_points, axis=1)
        phase = 2 * np.pi * (self.state.frequency * self.t - distances / 2)
        
        # Calculate current amplitude based on min and max current
        current_range = self.state.max_current - self.state.min_current
        current = self.state.min_current + (current_range * abs(np.sin(2 * np.pi * self.state.frequency * self.t)))
        
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

        @self.ctrl.trigger("tick")
        def on_tick():
            if self.ctrl.tick:
                self.update_scene()

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
                    
                    vuetify.VSlider(
                        v_model=("frequency", self.frequency),
                        min=0.1,
                        max=5.0,
                        step=0.1,
                        label="Frequency (Hz)",
                        thumb_label="always",
                        on_input=self.update_scene,
                        classes="mb-4"
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

            # Main content area
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
                    vtk.VtkRemoteView(
                        self.plotter.ren_win,
                        ref="view",
                        camera_parallel_projection=False,
                        interactor_settings={
                            "max_distance": 5.0,
                            "min_distance": 0.1
                        }
                    )

    def initialize_state(self):
        self.state.antenna_length = self.antenna_length
        self.state.min_current = self.min_current
        self.state.max_current = self.max_current
        self.state.frequency = self.frequency

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