"""
UAV Telemetry data structures and generator.
Produces realistic telemetry frames for different mission profiles.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import time
import json


@dataclass
class TelemetryFrame:
    """A single telemetry data point."""
    timestamp: float
    lat: float
    lon: float
    alt: float            # meters AGL
    vx: float             # m/s (North)
    vy: float             # m/s (East)
    vz: float             # m/s (Down, negative = climbing)
    battery: float        # percentage 0-100
    rssi: float           # signal strength dBm
    gps_fix: int          # 0=no fix, 2=2D, 3=3D
    flight_mode: str      # STABILIZE, GUIDED, AUTO, LOITER, RTL, LAND
    heading: float        # degrees 0-360
    roll: float           # degrees
    pitch: float          # degrees
    yaw: float            # degrees
    ground_speed: float   # m/s
    air_speed: float      # m/s
    satellites: int       # GPS satellite count
    armed: bool = True

    @property
    def speed_3d(self) -> float:
        return np.sqrt(self.vx**2 + self.vy**2 + self.vz**2)

    @property
    def position(self) -> tuple:
        return (self.lat, self.lon, self.alt)

    def to_dict(self) -> dict:
        return {
            "timestamp": round(self.timestamp, 2),
            "lat": round(self.lat, 7),
            "lon": round(self.lon, 7),
            "alt": round(self.alt, 2),
            "vx": round(self.vx, 2),
            "vy": round(self.vy, 2),
            "vz": round(self.vz, 2),
            "battery": round(self.battery, 1),
            "rssi": round(self.rssi, 1),
            "gps_fix": self.gps_fix,
            "flight_mode": self.flight_mode,
            "heading": round(self.heading, 1),
            "ground_speed": round(self.ground_speed, 2),
            "air_speed": round(self.air_speed, 2),
            "satellites": self.satellites,
            "roll": round(self.roll, 1),
            "pitch": round(self.pitch, 1),
            "yaw": round(self.yaw, 1),
            "armed": self.armed,
        }


class TelemetryGenerator:
    """
    Generates realistic UAV telemetry data for different mission profiles.

    Profiles:
    - Survey: Grid/lawnmower pattern at constant altitude
    - Inspection: Orbit around a point of interest
    - Racing: Fast waypoint-to-waypoint flight
    """

    # Base coordinates (Surabaya area for KRTI context)
    BASE_LAT = -7.2756
    BASE_LON = 112.7942

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_mission(self, profile: str = "survey",
                          duration: float = 300.0,
                          dt: float = 1.0) -> List[TelemetryFrame]:
        """
        Generate a full mission's telemetry data.

        Args:
            profile: "survey", "inspection", or "racing"
            duration: Mission duration in seconds
            dt: Time step in seconds

        Returns:
            List of TelemetryFrame objects
        """
        generators = {
            "survey": self._gen_survey,
            "inspection": self._gen_inspection,
            "racing": self._gen_racing,
        }
        gen_func = generators.get(profile, self._gen_survey)
        return gen_func(duration, dt)

    def _gen_survey(self, duration: float, dt: float) -> List[TelemetryFrame]:
        """Generate survey/grid pattern mission."""
        frames = []
        t = 0.0
        battery = 100.0
        alt = 0.0
        target_alt = 50.0

        # Grid parameters
        grid_width = 0.002   # ~220m in lon
        grid_length = 0.003  # ~330m in lat
        num_lines = 8
        speed = 8.0  # m/s

        lat = self.BASE_LAT
        lon = self.BASE_LON
        mode = "AUTO"
        direction = 1  # 1 = north, -1 = south
        line_idx = 0

        while t < duration:
            # Takeoff phase
            if t < 15:
                mode = "GUIDED"
                alt = min(target_alt, alt + 3.5 * dt)
                vz = -3.5 if alt < target_alt else 0
                vx, vy = 0, 0
            # Landing phase
            elif t > duration - 20:
                mode = "LAND"
                alt = max(0, alt - 2.5 * dt)
                vz = 2.5 if alt > 0 else 0
                vx, vy = 0, 0
            # Survey pattern
            else:
                mode = "AUTO"
                alt = target_alt + self.rng.normal(0, 0.3)
                vz = self.rng.normal(0, 0.2)

                # Move along grid line
                lat_delta = direction * speed * dt / 111000  # rough deg conversion
                lat += lat_delta
                vx = direction * speed + self.rng.normal(0, 0.3)
                vy = self.rng.normal(0, 0.2)

                # Check if we need to switch to next line
                if abs(lat - self.BASE_LAT) > grid_length / 2:
                    direction *= -1
                    lon += grid_width / num_lines
                    line_idx += 1

            # Battery drain: ~0.05%/s in cruise, more in climb
            if mode == "GUIDED":
                battery -= 0.08 * dt
            elif mode == "AUTO":
                battery -= 0.045 * dt
            else:
                battery -= 0.03 * dt
            battery = max(0, battery)

            # GPS noise
            gps_lat = lat + self.rng.normal(0, 2e-6)
            gps_lon = lon + self.rng.normal(0, 2e-6)

            heading = (np.degrees(np.arctan2(vy, vx)) + 360) % 360
            gs = np.sqrt(vx**2 + vy**2)

            frame = TelemetryFrame(
                timestamp=t,
                lat=gps_lat, lon=gps_lon, alt=max(0, alt),
                vx=vx, vy=vy, vz=vz,
                battery=battery,
                rssi=-45 + self.rng.normal(0, 3),
                gps_fix=3, flight_mode=mode,
                heading=heading,
                roll=self.rng.normal(0, 3),
                pitch=self.rng.normal(-2 if mode == "AUTO" else 0, 2),
                yaw=heading,
                ground_speed=gs,
                air_speed=gs + self.rng.normal(0, 0.5),
                satellites=max(6, int(12 + self.rng.normal(0, 2))),
                armed=battery > 0,
            )
            frames.append(frame)
            t += dt

        return frames

    def _gen_inspection(self, duration: float, dt: float) -> List[TelemetryFrame]:
        """Generate orbit/inspection pattern mission."""
        frames = []
        t = 0.0
        battery = 100.0
        alt = 0.0
        target_alt = 30.0
        orbit_radius = 0.0008  # ~90m
        orbit_speed = 0.5  # rad/s equivalent angular rate

        poi_lat = self.BASE_LAT
        poi_lon = self.BASE_LON

        while t < duration:
            if t < 12:
                mode = "GUIDED"
                alt = min(target_alt, alt + 3.0 * dt)
                lat, lon = poi_lat + orbit_radius, poi_lon
                vx, vy, vz = 0, 0, -3.0
            elif t > duration - 18:
                mode = "RTL"
                alt = max(0, alt - 2.0 * dt)
                lat, lon = poi_lat, poi_lon
                vx, vy, vz = 0, 0, 2.0
            else:
                mode = "LOITER"
                angle = orbit_speed * (t - 12) * 0.05
                lat = poi_lat + orbit_radius * np.cos(angle)
                lon = poi_lon + orbit_radius * np.sin(angle)
                alt = target_alt + 3 * np.sin(angle * 0.3) + self.rng.normal(0, 0.2)

                vx = -orbit_radius * orbit_speed * np.sin(angle) * 111000 * 0.05
                vy = orbit_radius * orbit_speed * np.cos(angle) * 111000 * 0.05
                vz = self.rng.normal(0, 0.3)

            battery -= (0.06 if mode == "LOITER" else 0.04) * dt
            battery = max(0, battery)

            heading = (np.degrees(np.arctan2(vy, vx)) + 360) % 360
            gs = np.sqrt(vx**2 + vy**2)

            # Simulate occasional RSSI dips
            rssi = -50 + self.rng.normal(0, 4)
            if self.rng.random() < 0.03:
                rssi -= 20  # Dropout

            frame = TelemetryFrame(
                timestamp=t,
                lat=lat + self.rng.normal(0, 1.5e-6),
                lon=lon + self.rng.normal(0, 1.5e-6),
                alt=max(0, alt),
                vx=vx, vy=vy, vz=vz,
                battery=battery,
                rssi=rssi,
                gps_fix=3,
                flight_mode=mode,
                heading=heading,
                roll=self.rng.normal(15 if mode == "LOITER" else 0, 3),
                pitch=self.rng.normal(0, 2),
                yaw=heading,
                ground_speed=gs,
                air_speed=gs + self.rng.normal(0, 0.4),
                satellites=max(5, int(11 + self.rng.normal(0, 2))),
                armed=battery > 0,
            )
            frames.append(frame)
            t += dt

        return frames

    def _gen_racing(self, duration: float, dt: float) -> List[TelemetryFrame]:
        """Generate fast racing/waypoint pattern mission."""
        frames = []
        t = 0.0
        battery = 100.0
        alt = 0.0
        target_alt = 15.0

        # Waypoints (relative offsets from base)
        waypoints = [
            (0, 0), (0.001, 0.002), (0.002, 0), (0.001, -0.002),
            (0, -0.001), (-0.001, 0.001), (-0.002, -0.001), (0, 0),
        ]
        wp_idx = 0
        lat = self.BASE_LAT
        lon = self.BASE_LON
        max_speed = 18.0

        while t < duration:
            if t < 8:
                mode = "GUIDED"
                alt = min(target_alt, alt + 4.0 * dt)
                vx, vy, vz = 0, 0, -4.0
            elif t > duration - 12:
                mode = "LAND"
                alt = max(0, alt - 3.0 * dt)
                vx, vy, vz = 0, 0, 3.0
            else:
                mode = "AUTO"
                # Navigate to current waypoint
                if wp_idx < len(waypoints):
                    target_lat = self.BASE_LAT + waypoints[wp_idx][0]
                    target_lon = self.BASE_LON + waypoints[wp_idx][1]

                    dlat = target_lat - lat
                    dlon = target_lon - lon
                    dist = np.sqrt(dlat**2 + dlon**2) * 111000

                    if dist < 5:  # Within 5m, next waypoint
                        wp_idx = (wp_idx + 1) % len(waypoints)
                    else:
                        speed = min(max_speed, dist * 0.3)
                        direction = np.arctan2(dlon, dlat)
                        vx = speed * np.cos(direction) + self.rng.normal(0, 0.5)
                        vy = speed * np.sin(direction) + self.rng.normal(0, 0.5)
                        lat += vx * dt / 111000
                        lon += vy * dt / 111000

                alt = target_alt + self.rng.normal(0, 0.5)
                vz = self.rng.normal(0, 0.4)

            battery -= 0.09 * dt  # Higher drain for racing
            battery = max(0, battery)

            heading = (np.degrees(np.arctan2(vy if 'vy' in dir() else 0,
                                              vx if 'vx' in dir() else 0)) + 360) % 360
            gs = np.sqrt((vx if 'vx' in dir() else 0)**2 +
                         (vy if 'vy' in dir() else 0)**2)

            frame = TelemetryFrame(
                timestamp=t,
                lat=lat + self.rng.normal(0, 1e-6),
                lon=lon + self.rng.normal(0, 1e-6),
                alt=max(0, alt),
                vx=vx if 'vx' in dir() else 0,
                vy=vy if 'vy' in dir() else 0,
                vz=vz if 'vz' in dir() else 0,
                battery=battery,
                rssi=-40 + self.rng.normal(0, 5),
                gps_fix=3,
                flight_mode=mode,
                heading=heading,
                roll=self.rng.normal(0, 8),
                pitch=self.rng.normal(-5 if gs > 10 else 0, 3),
                yaw=heading,
                ground_speed=gs,
                air_speed=gs + self.rng.normal(1, 0.5),
                satellites=max(6, int(10 + self.rng.normal(0, 2))),
                armed=battery > 0,
            )
            frames.append(frame)
            t += dt

        return frames

    @staticmethod
    def frames_to_dataframe(frames: List[TelemetryFrame]):
        """Convert frames list to a pandas DataFrame."""
        import pandas as pd
        return pd.DataFrame([f.to_dict() for f in frames])
