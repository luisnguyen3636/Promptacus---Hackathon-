"""Spatial registry for named cameras, geographic bearing calculation, and blind-spot routing."""

import math
from typing import Dict, List, Optional, Tuple

from urbansoc.topology.models import (
    BlindSpotRoute,
    BlindSpotZone,
    ExitGateConfig,
    NamedCameraNode,
)


def compute_geographic_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing (0-360 degrees) from coordinate 1 to coordinate 2."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon_r = math.radians(lon2 - lon1)

    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - (math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r))

    initial_bearing = math.atan2(x, y)
    compass_bearing = (math.degrees(initial_bearing) + 360) % 360
    return round(compass_bearing, 1)


def compute_haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance in meters using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2
         + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 1)


def is_point_inside_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting algorithm to test whether normalized point (x, y) is inside polygon."""
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class NamedCameraRegistry:
    """Master Spatial Repository for all named camera nodes and interconnected blind spot topology."""

    def __init__(self) -> None:
        self.cameras: Dict[str, NamedCameraNode] = {}
        self.blind_spots: Dict[str, BlindSpotZone] = {}
        self._initialize_default_urban_topology()

    def register_camera(self, node: NamedCameraNode) -> None:
        self.cameras[node.camera_id] = node

    def get_camera(self, camera_id_or_name: str) -> Optional[NamedCameraNode]:
        """Lookup camera node by camera_id or exact/partial camera_name."""
        if camera_id_or_name in self.cameras:
            return self.cameras[camera_id_or_name]

        # Case-insensitive partial name match
        query = camera_id_or_name.lower().strip()
        for node in self.cameras.values():
            if query == node.camera_name.lower().strip() or query in node.camera_name.lower():
                return node
        return None

    def match_exit_gate(
        self,
        camera_id_or_name: str,
        bbox_norm: Tuple[float, float, float, float],
        velocity_vector: Tuple[float, float] = (0.0, 0.0),
    ) -> Optional[ExitGateConfig]:
        """Determine if suspect's bottom center BBox and velocity vector match an Exit Gate."""
        node = self.get_camera(camera_id_or_name)
        if not node or not node.exit_gates:
            return None

        # Bottom center coordinate
        x1, y1, x2, y2 = bbox_norm
        bottom_center_x = (x1 + x2) / 2.0
        bottom_center_y = y2

        # 1. Exact polygon containment check
        for gate in node.exit_gates.values():
            if is_point_inside_polygon(bottom_center_x, bottom_center_y, gate.polygon_coords):
                return gate

        # 2. Frame margin proximity check (within 10% of frame boundary aligned with velocity)
        vx, vy = velocity_vector
        if bottom_center_x >= 0.88 and vx > 0.0:
            for g in node.exit_gates.values():
                if "EAST" in g.gate_id:
                    return g
        elif bottom_center_x <= 0.12 and vx < 0.0:
            for g in node.exit_gates.values():
                if "WEST" in g.gate_id:
                    return g
        elif bottom_center_y >= 0.90 and vy > 0.0:
            for g in node.exit_gates.values():
                if "SOUTH" in g.gate_id:
                    return g
        elif bottom_center_y <= 0.15 and vy < 0.0:
            for g in node.exit_gates.values():
                if "NORTH" in g.gate_id:
                    return g

        # Default fallback to first exit gate if velocity points toward it
        if node.exit_gates:
            return list(node.exit_gates.values())[0]

        return None

    def get_blind_spot_zone(self, zone_id: str) -> Optional[BlindSpotZone]:
        return self.blind_spots.get(zone_id)

    def resolve_connected_cameras(
        self,
        origin_camera_id: str,
        blind_spot_id: Optional[str] = None,
        exit_heading_deg: Optional[float] = None,
    ) -> List[BlindSpotRoute]:
        """Retrieve all candidate routes and target cameras from the origin camera."""
        origin_node = self.get_camera(origin_camera_id)
        if not origin_node:
            return []

        # If blind spot is explicitly specified
        if blind_spot_id and blind_spot_id in self.blind_spots:
            zone = self.blind_spots[blind_spot_id]
            # Exclude self-loop routes back to same camera
            return [r for r in zone.routes if r.target_camera_id != origin_node.camera_id]

        # Automatic spatial bridging across adjacent blind spots
        candidate_routes: List[BlindSpotRoute] = []
        for bs_id in origin_node.connected_blind_spots:
            if bs_id in self.blind_spots:
                for r in self.blind_spots[bs_id].routes:
                    if r.target_camera_id != origin_node.camera_id:
                        candidate_routes.append(r)

        if candidate_routes:
            return candidate_routes

        # Fallback: compute direct geographic bearing to all other cameras in registry
        dynamic_routes: List[BlindSpotRoute] = []
        for target_id, target_node in self.cameras.items():
            if target_id == origin_node.camera_id:
                continue
            bearing = compute_geographic_bearing(
                origin_node.gps_lat, origin_node.gps_lng,
                target_node.gps_lat, target_node.gps_lng,
            )
            dist = compute_haversine_distance_meters(
                origin_node.gps_lat, origin_node.gps_lng,
                target_node.gps_lat, target_node.gps_lng,
            )
            route = BlindSpotRoute(
                route_id=f"DYN_{origin_node.camera_id}_TO_{target_id}",
                target_camera_id=target_id,
                target_camera_name=target_node.camera_name,
                target_camera_location=target_node.physical_location,
                distance_meters=dist if dist > 0 else 45.0,
                route_description=f"Lộ trình trực diện hướng {bearing}° qua hành lang đô thị",
                expected_entry_gate="WEST_EDGE" if bearing < 180 else "EAST_EDGE",
                optimal_heading_deg=bearing,
                friction_penalty=0.05,
                features=["URBAN_STREET", "ALLEYWAY"],
            )
            dynamic_routes.append(route)

        return dynamic_routes

    def _initialize_default_urban_topology(self) -> None:
        """Seed rich, realistic default multi-camera topology for Urban Safety AI-SOC."""
        # 1. Camera Nodes
        cam01 = NamedCameraNode(
            camera_id="CAM_01",
            camera_name="CAM_01 - Cổng Trường Chu Văn An",
            physical_location="Ngã ba Chu Văn An - Đinh Bộ Lĩnh, P.12, Bình Thạnh",
            gps_lat=10.803450,
            gps_lng=106.702310,
            azimuth_deg=90.0,  # Nhìn hướng Đông
            exit_gates={
                "EAST_ALLEY_GATE": ExitGateConfig(
                    gate_id="EAST_ALLEY_GATE",
                    polygon_coords=[(0.75, 0.20), (1.0, 0.20), (1.0, 0.95), (0.75, 0.95)],
                    connected_blind_spot_id="BS_ZONE_01",
                    compass_bearing_deg=115.0,
                    gate_description="Lối thông vào Hẻm 12 nhánh đông dẫn sang Bãi xe",
                ),
                "SOUTH_STREET_EDGE": ExitGateConfig(
                    gate_id="SOUTH_STREET_EDGE",
                    polygon_coords=[(0.20, 0.85), (0.80, 0.85), (0.80, 1.0), (0.20, 1.0)],
                    connected_blind_spot_id="BS_ZONE_02",
                    compass_bearing_deg=180.0,
                    gate_description="Đường Đinh Bộ Lĩnh xuôi về Ngã tư Nguyễn Xí",
                ),
            },
            connected_blind_spots=["BS_ZONE_01", "BS_ZONE_02"],
        )

        cam02 = NamedCameraNode(
            camera_id="CAM_02",
            camera_name="CAM_02 - Hẻm 12 Đinh Bộ Lĩnh",
            physical_location="Hẻm 12, P.12, Bình Thạnh (Hành lang nhánh sau trường)",
            gps_lat=10.803200,
            gps_lng=106.703200,
            azimuth_deg=270.0,  # Nhìn hướng Tây ngược lại
            exit_gates={
                "WEST_ALLEY_ENTRY": ExitGateConfig(
                    gate_id="WEST_ALLEY_ENTRY",
                    polygon_coords=[(0.0, 0.20), (0.25, 0.20), (0.25, 0.95), (0.0, 0.95)],
                    connected_blind_spot_id="BS_ZONE_01",
                    compass_bearing_deg=295.0,
                    gate_description="Cổng phía Tây nối từ Cổng trường Chu Văn An",
                ),
                "EAST_PARKING_EXIT": ExitGateConfig(
                    gate_id="EAST_PARKING_EXIT",
                    polygon_coords=[(0.80, 0.30), (1.0, 0.30), (1.0, 0.95), (0.80, 0.95)],
                    connected_blind_spot_id="BS_ZONE_03",
                    compass_bearing_deg=95.0,
                    gate_description="Lối rẽ vào bãi giữ xe máy Khu B",
                ),
            },
            connected_blind_spots=["BS_ZONE_01", "BS_ZONE_03"],
        )

        cam03 = NamedCameraNode(
            camera_id="CAM_03",
            camera_name="CAM_03 - Bãi Xe Khu B",
            physical_location="Khuông viên Bãi giữ xe máy Khu B, P.12, Bình Thạnh",
            gps_lat=10.802950,
            gps_lng=106.704100,
            azimuth_deg=180.0,  # Nhìn hướng Nam
            exit_gates={
                "NORTH_ALLEY_ENTRY": ExitGateConfig(
                    gate_id="NORTH_ALLEY_ENTRY",
                    polygon_coords=[(0.10, 0.0), (0.50, 0.0), (0.50, 0.25), (0.10, 0.25)],
                    connected_blind_spot_id="BS_ZONE_03",
                    compass_bearing_deg=0.0,
                    gate_description="Cổng thông từ Hẻm 12 vào bãi xe",
                ),
            },
            connected_blind_spots=["BS_ZONE_03"],
        )

        cam04 = NamedCameraNode(
            camera_id="CAM_04",
            camera_name="CAM_04 - Ngã Tư Nguyễn Xí",
            physical_location="Giao lộ Đinh Bộ Lĩnh - Nguyễn Xí, P.26, Bình Thạnh",
            gps_lat=10.801800,
            gps_lng=106.702800,
            azimuth_deg=0.0,  # Nhìn hướng Bắc đón người từ Chu Văn An xuống
            exit_gates={
                "NORTH_MAIN_STREET": ExitGateConfig(
                    gate_id="NORTH_MAIN_STREET",
                    polygon_coords=[(0.20, 0.0), (0.80, 0.0), (0.80, 0.20), (0.20, 0.20)],
                    connected_blind_spot_id="BS_ZONE_02",
                    compass_bearing_deg=0.0,
                    gate_description="Trục đường chính đón người từ Cổng trường Chu Văn An",
                ),
            },
            connected_blind_spots=["BS_ZONE_02"],
        )

        self.register_camera(cam01)
        self.register_camera(cam02)
        self.register_camera(cam03)
        self.register_camera(cam04)

        # 2. Blind Spot Zones connecting the cameras
        self.blind_spots["BS_ZONE_01"] = BlindSpotZone(
            zone_id="BS_ZONE_01",
            name="Vùng mù Hẻm 12 nhánh ngắn",
            description="Đoạn hẻm quanh co 35m có nhiều thùng rác công cộng và lối thông sang bãi giữ xe",
            has_dumping_spots=True,
            has_vehicle_access=True,
            routes=[
                BlindSpotRoute(
                    route_id="ROUTE_CAM01_TO_CAM02_SHORT_ALLEY",
                    target_camera_id="CAM_02",
                    target_camera_name="CAM_02 - Hẻm 12 Đinh Bộ Lĩnh",
                    target_camera_location="Hẻm 12, P.12, Bình Thạnh",
                    distance_meters=35.0,
                    route_description="Luồn theo đường hẻm phụ 35m qua góc cua 90 độ có điểm tập kết rác",
                    expected_entry_gate="WEST_ALLEY_ENTRY",
                    friction_penalty=0.10,
                    features=["TRASH_BIN", "DARK_ALLEY", "NARROW_PASSAGE"],
                    optimal_heading_deg=115.0,
                ),
                BlindSpotRoute(
                    route_id="ROUTE_CAM01_TO_CAM03_BYPASS",
                    target_camera_id="CAM_03",
                    target_camera_name="CAM_03 - Bãi Xe Khu B",
                    target_camera_location="Khuôn viên Bãi giữ xe máy Khu B",
                    distance_meters=85.0,
                    route_description="Chạy tắt qua đường luồn dân cư thẳng ra bãi đỗ xe máy",
                    expected_entry_gate="NORTH_ALLEY_ENTRY",
                    friction_penalty=0.25,
                    features=["PARKING_LOT", "MOTORBIKE_STAND", "EVACUATION_GATE"],
                    optimal_heading_deg=135.0,
                ),
            ],
        )

        self.blind_spots["BS_ZONE_02"] = BlindSpotZone(
            zone_id="BS_ZONE_02",
            name="Vùng mù Trục đường Đinh Bộ Lĩnh",
            description="Trục đường nhựa thẳng 160m, lòng đường rộng 12m, tầm nhìn thoáng, đèn đường sáng",
            has_dumping_spots=False,
            has_vehicle_access=True,
            routes=[
                BlindSpotRoute(
                    route_id="ROUTE_CAM01_TO_CAM04_MAIN_ROAD",
                    target_camera_id="CAM_04",
                    target_camera_name="CAM_04 - Ngã Tư Nguyễn Xí",
                    target_camera_location="Giao lộ Đinh Bộ Lĩnh - Nguyễn Xí",
                    distance_meters=160.0,
                    route_description="Chạy nước rút dọc theo vỉa hè Đinh Bộ Lĩnh xuôi về Ngã tư Nguyễn Xí",
                    expected_entry_gate="NORTH_MAIN_STREET",
                    friction_penalty=0.0,
                    features=["WIDE_ROAD", "HIGH_VISIBILITY", "SPEED_SPRINT"],
                    optimal_heading_deg=180.0,
                ),
            ],
        )

        self.blind_spots["BS_ZONE_03"] = BlindSpotZone(
            zone_id="BS_ZONE_03",
            name="Vùng mù Lối vào Bãi xe",
            description="Đoạn cua hẹp có rào chắn barrier 25m dẫn vào cổng bãi xe B",
            has_dumping_spots=True,
            has_vehicle_access=True,
            routes=[
                BlindSpotRoute(
                    route_id="ROUTE_CAM02_TO_CAM03_GATE",
                    target_camera_id="CAM_03",
                    target_camera_name="CAM_03 - Bãi Xe Khu B",
                    target_camera_location="Khuôn viên Bãi giữ xe máy Khu B",
                    distance_meters=25.0,
                    route_description="Băng qua barrier vào bãi giữ xe máy",
                    expected_entry_gate="NORTH_ALLEY_ENTRY",
                    friction_penalty=0.05,
                    features=["PARKING_LOT", "BARRIER"],
                    optimal_heading_deg=95.0,
                ),
            ],
        )
