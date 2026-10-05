"""
3D Trajectory simulator with Bézier interpolation and wind model.
"""

import numpy as np
from typing import List, Tuple, Optional


class TrajectorySimulator:
    """
    Generates smooth 3D UAV trajectories using Bézier curve interpolation
    with optional wind disturbance and turbulence models.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def bezier_curve(self, control_points: np.ndarray,
                     num_points: int = 100) -> np.ndarray:
        """
        Generate a Bézier curve from control points.

        Args:
            control_points: Nx3 array of control points (lat, lon, alt)
            num_points: Number of output points

        Returns:
            num_points x 3 array of interpolated points
        """
        n = len(control_points) - 1
        t = np.linspace(0, 1, num_points)
        curve = np.zeros((num_points, 3))

        for i in range(n + 1):
            # Bernstein polynomial
            binom = np.math.factorial(n) / (np.math.factorial(i) * np.math.factorial(n - i))
            basis = binom * (t ** i) * ((1 - t) ** (n - i))
            curve += np.outer(basis, control_points[i])

        return curve

    def generate_waypoint_trajectory(self, waypoints: List[Tuple[float, float, float]],
                                      points_per_segment: int = 50,
                                      smoothness: float = 0.3) -> np.ndarray:
        """
        Generate a smooth trajectory through waypoints.

        Args:
            waypoints: List of (lat, lon, alt) tuples
            points_per_segment: Points between each pair of waypoints
            smoothness: Control point offset factor (0-1)

        Returns:
            Nx3 array of trajectory points
        """
        if len(waypoints) < 2:
            return np.array(waypoints)

        all_points = []
        wp_arr = np.array(waypoints)

        for i in range(len(wp_arr) - 1):
            p0 = wp_arr[i]
            p3 = wp_arr[i + 1]

            # Generate smooth control points
            if i > 0:
                tangent = wp_arr[i] - wp_arr[i - 1]
                p1 = p0 + smoothness * tangent
            else:
                p1 = p0 + smoothness * (p3 - p0)

            if i < len(wp_arr) - 2:
                tangent = wp_arr[i + 2] - wp_arr[i + 1]
                p2 = p3 - smoothness * tangent
            else:
                p2 = p3 - smoothness * (p3 - p0)

            segment = self.bezier_curve(
                np.array([p0, p1, p2, p3]),
                points_per_segment
            )
            all_points.append(segment[:-1] if i < len(wp_arr) - 2 else segment)

        return np.vstack(all_points)

    def apply_wind(self, trajectory: np.ndarray,
                   wind_speed: float = 3.0,
                   wind_direction: float = 45.0,
                   turbulence: float = 0.5) -> np.ndarray:
        """
        Apply wind disturbance to a trajectory.

        Args:
            trajectory: Nx3 array of points
            wind_speed: Wind speed in m/s
            wind_direction: Wind direction in degrees (0=North)
            turbulence: Turbulence intensity (0-1)

        Returns:
            Disturbed trajectory
        """
        n = len(trajectory)
        disturbed = trajectory.copy()

        # Convert wind to lat/lon deltas
        wind_rad = np.radians(wind_direction)
        wind_lat = wind_speed * np.cos(wind_rad) / 111000  # rough deg/s
        wind_lon = wind_speed * np.sin(wind_rad) / 111000

        # Cumulative wind effect (increases over time)
        t = np.linspace(0, 1, n)
        wind_effect_lat = wind_lat * t * 0.01  # Scale down for realism
        wind_effect_lon = wind_lon * t * 0.01

        # Turbulence (random walk)
        turb_lat = np.cumsum(self.rng.normal(0, turbulence * 1e-6, n))
        turb_lon = np.cumsum(self.rng.normal(0, turbulence * 1e-6, n))
        turb_alt = np.cumsum(self.rng.normal(0, turbulence * 0.05, n))

        disturbed[:, 0] += wind_effect_lat + turb_lat
        disturbed[:, 1] += wind_effect_lon + turb_lon
        disturbed[:, 2] += turb_alt

        return disturbed

    def generate_predefined_missions(self) -> dict:
        """
        Generate predefined mission trajectories.

        Returns:
            Dict of mission_name -> trajectory array
        """
        missions = {}

        # Survey grid
        survey_wps = []
        base_lat, base_lon = -7.2756, 112.7942
        alt = 50.0
        lines = 6
        for i in range(lines):
            if i % 2 == 0:
                survey_wps.append((base_lat, base_lon + i * 0.0003, alt))
                survey_wps.append((base_lat + 0.003, base_lon + i * 0.0003, alt))
            else:
                survey_wps.append((base_lat + 0.003, base_lon + i * 0.0003, alt))
                survey_wps.append((base_lat, base_lon + i * 0.0003, alt))
        missions["survey"] = self.generate_waypoint_trajectory(survey_wps, 30)

        # Inspection orbit
        orbit_points = []
        center_lat, center_lon = base_lat + 0.001, base_lon + 0.001
        radius = 0.0008
        for angle in np.linspace(0, 2 * np.pi, 40):
            orbit_points.append((
                center_lat + radius * np.cos(angle),
                center_lon + radius * np.sin(angle),
                30 + 5 * np.sin(angle * 2),
            ))
        missions["inspection"] = np.array(orbit_points)

        # Racing course
        racing_wps = [
            (base_lat, base_lon, 15),
            (base_lat + 0.001, base_lon + 0.002, 15),
            (base_lat + 0.002, base_lon, 20),
            (base_lat + 0.001, base_lon - 0.002, 15),
            (base_lat, base_lon - 0.001, 10),
            (base_lat - 0.001, base_lon + 0.001, 15),
            (base_lat, base_lon, 15),
        ]
        missions["racing"] = self.generate_waypoint_trajectory(racing_wps, 40)

        return missions
