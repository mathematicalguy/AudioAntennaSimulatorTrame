# trame_antenna_sim.py
import numpy as np
import pyvista as pv
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify, html
import asyncio
import time

try:
    # Initialize server with specific host and port and launcher
    server = get_server(
        host="localhost", 
        port=8080, 
        client_type='vue2',
        allow_multi_clients=True
    )
    state, ctrl = server.state, server.controller

    # Simulation Parameters
    antenna_length = 1.0
    antenna_radius = 0.02
    current_amplitude = 1.0
    frequency = 1.0
    time_step = 0.05
    t = 0.0

    # Field points
    def generate_field_points():
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

    field_points = generate_field_points()
    vectors = np.zeros_like(field_points)
    field_data = pv.PolyData(field_points)
    field_data["E"] = vectors

    # Create Antenna
    def make_antenna(length):
        body = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=antenna_radius, height=length)
        base = pv.Cylinder(center=(0, 0, -length/20), direction=(0, 0, 1), radius=antenna_radius*3, height=length/10)
        top = pv.Sphere(center=(0, 0, length), radius=antenna_radius*1.5)
        return body + base + top

    # Plotter Setup
    plotter = pv.Plotter(off_screen=True)
    plotter.set_background("black")
    plotter.background_color = "black"  # Add explicit background color
    plotter.renderer.SetBackground(0, 0, 0)  # Set renderer background explicitly
    antenna_actor = plotter.add_mesh(make_antenna(antenna_length), color="silver", name="antenna")

    # Field visualization
    def update_scene(**kwargs):
        global t
        t += time_step
        plotter.remove_actor("antenna")
        plotter.add_mesh(make_antenna(state.antenna_length), color="silver", name="antenna")
        
        distances = np.linalg.norm(field_points, axis=1)
        phase = 2 * np.pi * (state.frequency * t - distances / 2)
        vectors[:, 0] = state.current * np.sin(phase) * field_points[:, 0] / distances
        vectors[:, 1] = state.current * np.sin(phase) * field_points[:, 1] / distances
        vectors[:, 2] = state.current * np.cos(phase) * np.cos(np.arctan2(distances, field_points[:, 2]))

        intensities = np.linalg.norm(vectors, axis=1)
        field_data["E"] = vectors
        field_data["intensity"] = intensities
        glyphs = field_data.glyph(orient="E", scale="intensity", factor=0.1)
        
        plotter.remove_actor("field")
        plotter.add_mesh(glyphs, scalars="intensity", cmap="plasma", name="field", opacity=0.8)
        
        # Update the visualization without using view_update
        if plotter.ren_win:
            plotter.render()
            plotter.ren_win.Modified()
            plotter.ren_win.Render()

    ctrl.on_server_ready.add(update_scene)

    # Instead of using Timer, we'll use trame's built-in periodic_callback
    @state.change("server_ready")
    def on_ready(ready=False, **kwargs):
        if ready:
            update_scene()
            ctrl.tick_period = 50  # 50ms between updates
            ctrl.tick = True

    @ctrl.trigger("tick")
    def on_tick():
        if ctrl.tick:
            update_scene()

    # UI Layout
    with SinglePageLayout(server) as layout:
        layout.title.set_text("Antenna Field Simulation")
        with layout.content:
            vtk.VtkRemoteView(plotter.ren_win, ref="view")

            with vuetify.VContainer():
                vuetify.VSlider(
                    v_model=("antenna_length", antenna_length),
                    min=0.2,
                    max=2.0,
                    step=0.05,
                    label="Antenna Length",
                    on_input=update_scene
                )
                vuetify.VSlider(
                    v_model=("current", current_amplitude),
                    min=0.1,
                    max=3.0,
                    step=0.1,
                    label="Current (A)",
                    on_input=update_scene
                )
                vuetify.VSlider(
                    v_model=("frequency", frequency),
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    label="Frequency (Hz)",
                    on_input=update_scene
                )

    # Start server
    if __name__ == "__main__":
        print("Starting Antenna Field Simulation Server...")
        print("Access the visualization at http://localhost:8080")
        state.antenna_length = antenna_length
        state.current = current_amplitude
        state.frequency = frequency
        
        # Add command line argument handling
        import sys
        if '--server' in sys.argv:
            server.start(show_server_only=True)  # Prevent browser from opening
        else:
            server.start()

except Exception as e:
    print(f"An error occurred: {str(e)}")
    print("Please ensure all dependencies are installed correctly:")