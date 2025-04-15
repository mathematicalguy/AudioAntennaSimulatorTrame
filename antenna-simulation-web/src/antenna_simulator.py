import numpy as np
import pyvista as pv

class AntennaSimulator:
    def __init__(self):
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
        self.antenna_mesh = None
        self.update_antenna_mesh()

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

    def make_antenna(self, length, antenna_type):
        if antenna_type == 'Dipole':
            return self._make_dipole(length)
        elif antenna_type == 'Monopole':
            return self._make_monopole(length)
        elif antenna_type == 'Loop':
            return self._make_loop(length)
        elif antenna_type == 'Yagi':
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

    def get_actual_frequency(self):
        """Convert the frequency value based on the selected unit"""
        return self.frequency * self.freq_multipliers[self.freq_unit]

    def update_simulation(self, **params):
        """Update simulation parameters and calculate the next time step"""
        # Update parameters if provided
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
        # Update antenna mesh if length or type changed
        if 'antenna_length' in params or 'antenna_type' in params:
            self.update_antenna_mesh()
        
        # Update time
        self.t += self.time_step
        
        # Recalculate field
        self.update_field_vectors()
        
        return {
            'antenna_mesh': self.antenna_mesh,
            'field_data': self.field_data
        }
    
    def update_antenna_mesh(self):
        """Update the antenna mesh based on current parameters"""
        self.antenna_mesh = self.make_antenna(self.antenna_length, self.antenna_type)
        
    def update_field_vectors(self):
        """Update the electric field vectors"""
        distances = np.linalg.norm(self.field_points, axis=1)
        actual_freq = self.get_actual_frequency()
        phase = 2 * np.pi * (actual_freq * self.t - distances / 2)
        
        # Calculate current amplitude based on min and max current
        current_range = self.max_current - self.min_current
        current = self.min_current + (current_range * abs(np.sin(2 * np.pi * actual_freq * self.t)))
        
        self.vectors[:, 0] = current * np.sin(phase) * self.field_points[:, 0] / distances
        self.vectors[:, 1] = current * np.sin(phase) * self.field_points[:, 1] / distances
        self.vectors[:, 2] = current * np.cos(phase) * np.cos(np.arctan2(distances, self.field_points[:, 2]))

        intensities = np.linalg.norm(self.vectors, axis=1)
        self.field_data["E"] = self.vectors
        self.field_data["intensity"] = intensities