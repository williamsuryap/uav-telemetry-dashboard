"""
Alert engine for UAV telemetry monitoring.
Provides threshold-based alerting with severity levels.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time


@dataclass
class Alert:
    """A telemetry alert."""
    timestamp: float
    severity: str       # "INFO", "WARNING", "CRITICAL"
    category: str       # "BATTERY", "ALTITUDE", "RSSI", "GEOFENCE", "GPS", "SPEED"
    message: str
    value: float
    threshold: float

    @property
    def severity_emoji(self) -> str:
        return {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "CRITICAL": "🚨"
        }.get(self.severity, "❓")

    @property
    def category_emoji(self) -> str:
        return {
            "BATTERY": "🔋",
            "ALTITUDE": "📏",
            "RSSI": "📡",
            "GEOFENCE": "🗺️",
            "GPS": "🛰️",
            "SPEED": "💨",
        }.get(self.category, "📌")

    @property
    def time_str(self) -> str:
        mins = int(self.timestamp) // 60
        secs = int(self.timestamp) % 60
        return f"T+{mins:02d}:{secs:02d}"


class AlertEngine:
    """
    Threshold-based alert engine for UAV telemetry.

    Monitors key parameters and generates alerts when thresholds
    are breached. Supports configurable thresholds and cooldown
    to avoid alert spam.
    """

    DEFAULT_THRESHOLDS = {
        "battery_warning": 30.0,         # %
        "battery_critical": 15.0,        # %
        "altitude_max": 120.0,           # meters
        "altitude_min": 2.0,             # meters (when armed)
        "rssi_warning": -70.0,           # dBm
        "rssi_critical": -85.0,          # dBm
        "speed_max": 25.0,               # m/s
        "gps_min_satellites": 6,         # count
        "geofence_radius": 500.0,        # meters from home
    }

    def __init__(self, thresholds: Optional[Dict] = None,
                 cooldown: float = 10.0):
        """
        Args:
            thresholds: Custom threshold dict (merged with defaults)
            cooldown: Minimum seconds between same-category alerts
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)

        self.cooldown = cooldown
        self.alerts: List[Alert] = []
        self.last_alert_time: Dict[str, float] = {}
        self.home_lat: Optional[float] = None
        self.home_lon: Optional[float] = None

    def check(self, frame) -> List[Alert]:
        """
        Check a telemetry frame for alert conditions.

        Args:
            frame: TelemetryFrame object

        Returns:
            List of new Alert objects
        """
        new_alerts = []

        # Set home position from first frame
        if self.home_lat is None:
            self.home_lat = frame.lat
            self.home_lon = frame.lon

        # Battery checks
        if frame.battery <= self.thresholds["battery_critical"]:
            alert = self._create_alert(
                frame.timestamp, "CRITICAL", "BATTERY",
                f"Battery critically low: {frame.battery:.1f}%",
                frame.battery, self.thresholds["battery_critical"]
            )
            if alert:
                new_alerts.append(alert)
        elif frame.battery <= self.thresholds["battery_warning"]:
            alert = self._create_alert(
                frame.timestamp, "WARNING", "BATTERY",
                f"Battery low: {frame.battery:.1f}%",
                frame.battery, self.thresholds["battery_warning"]
            )
            if alert:
                new_alerts.append(alert)

        # Altitude checks
        if frame.alt > self.thresholds["altitude_max"]:
            alert = self._create_alert(
                frame.timestamp, "WARNING", "ALTITUDE",
                f"Altitude exceeded: {frame.alt:.1f}m (max: {self.thresholds['altitude_max']}m)",
                frame.alt, self.thresholds["altitude_max"]
            )
            if alert:
                new_alerts.append(alert)

        # RSSI checks
        if frame.rssi <= self.thresholds["rssi_critical"]:
            alert = self._create_alert(
                frame.timestamp, "CRITICAL", "RSSI",
                f"Signal lost: {frame.rssi:.0f} dBm",
                frame.rssi, self.thresholds["rssi_critical"]
            )
            if alert:
                new_alerts.append(alert)
        elif frame.rssi <= self.thresholds["rssi_warning"]:
            alert = self._create_alert(
                frame.timestamp, "WARNING", "RSSI",
                f"Weak signal: {frame.rssi:.0f} dBm",
                frame.rssi, self.thresholds["rssi_warning"]
            )
            if alert:
                new_alerts.append(alert)

        # Speed check
        if frame.ground_speed > self.thresholds["speed_max"]:
            alert = self._create_alert(
                frame.timestamp, "WARNING", "SPEED",
                f"Overspeed: {frame.ground_speed:.1f} m/s",
                frame.ground_speed, self.thresholds["speed_max"]
            )
            if alert:
                new_alerts.append(alert)

        # GPS check
        if frame.satellites < self.thresholds["gps_min_satellites"]:
            alert = self._create_alert(
                frame.timestamp, "WARNING", "GPS",
                f"Low satellite count: {frame.satellites}",
                frame.satellites, self.thresholds["gps_min_satellites"]
            )
            if alert:
                new_alerts.append(alert)

        # Geofence check
        if self.home_lat is not None:
            dist = self._haversine(self.home_lat, self.home_lon,
                                    frame.lat, frame.lon)
            if dist > self.thresholds["geofence_radius"]:
                alert = self._create_alert(
                    frame.timestamp, "CRITICAL", "GEOFENCE",
                    f"Geofence breach: {dist:.0f}m from home",
                    dist, self.thresholds["geofence_radius"]
                )
                if alert:
                    new_alerts.append(alert)

        return new_alerts

    def _create_alert(self, timestamp: float, severity: str,
                      category: str, message: str,
                      value: float, threshold: float) -> Optional[Alert]:
        """Create an alert if cooldown has elapsed."""
        key = f"{category}_{severity}"
        last = self.last_alert_time.get(key, -999)

        if timestamp - last < self.cooldown:
            return None

        alert = Alert(
            timestamp=timestamp,
            severity=severity,
            category=category,
            message=message,
            value=value,
            threshold=threshold,
        )
        self.alerts.append(alert)
        self.last_alert_time[key] = timestamp
        return alert

    def get_alerts_dataframe_data(self) -> List[Dict]:
        """Get alerts formatted for DataFrame display."""
        rows = []
        for alert in self.alerts:
            rows.append({
                "Time": alert.time_str,
                "Severity": f"{alert.severity_emoji} {alert.severity}",
                "Category": f"{alert.category_emoji} {alert.category}",
                "Message": alert.message,
                "Value": f"{alert.value:.1f}",
                "Threshold": f"{alert.threshold:.1f}",
            })
        return rows

    def get_summary(self) -> Dict:
        """Get alert summary."""
        return {
            "total": len(self.alerts),
            "critical": sum(1 for a in self.alerts if a.severity == "CRITICAL"),
            "warning": sum(1 for a in self.alerts if a.severity == "WARNING"),
            "info": sum(1 for a in self.alerts if a.severity == "INFO"),
            "categories": list(set(a.category for a in self.alerts)),
        }

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two GPS coordinates."""
        import math
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (math.sin(dphi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def reset(self):
        """Reset alert engine state."""
        self.alerts.clear()
        self.last_alert_time.clear()
        self.home_lat = None
        self.home_lon = None
