"""Pairwise and multi-person dangerous interaction analysis: Fighting, Snatching, Pursuit, Restraining, Surrounding."""

import math
from typing import Dict, List, Optional, Tuple

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import iou_xyxy
from urbansoc.domain.schemas import BehaviorPrediction, HumanPoseTrack, TrackHistoryState


def compute_vector_cosine_similarity(v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
    """Compute cosine similarity between two 2D movement vectors [-1.0, 1.0]."""
    mag1 = math.hypot(v1[0], v1[1])
    mag2 = math.hypot(v2[0], v2[1])
    if mag1 < 1e-4 or mag2 < 1e-4:
        return 0.0
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    return max(-1.0, min(1.0, dot / (mag1 * mag2)))


def analyze_multi_person_interactions(
    poses: List[HumanPoseTrack],
    states_by_id: Dict[int, TrackHistoryState],
    confirmed_behaviors_by_id: Dict[int, str],
    histories_by_id: Optional[Dict[int, List[TrackHistoryState]]] = None,
    fight_distance_norm: float = 1.35,
    fight_wrist_energy_thresh: float = 1200.0,
) -> Dict[int, BehaviorPrediction]:
    """Detect complex dangerous interactions: Fighting, Snatching, Pursuit, Restraining, Surrounding.

    Applies spatial and kinematic gates to systematically suppress false positives.
    """
    interaction_predictions: Dict[int, BehaviorPrediction] = {}
    num_poses = len(poses)
    if num_poses < 2:
        return interaction_predictions

    # Priority 1: Multi-target Surrounding (>= 3 attackers enclosing 1 target)
    if num_poses >= 4:
        for target_idx, target_pose in enumerate(poses):
            target_c = target_pose.bbox.centroid
            target_h = float(target_pose.bbox.height)
            enclosing_subjects = []

            for other_idx, other_pose in enumerate(poses):
                if target_idx == other_idx:
                    continue
                d = math.hypot(target_c[0] - other_pose.bbox.centroid[0], target_c[1] - other_pose.bbox.centroid[1])
                if d <= (target_h * 2.5):
                    enclosing_subjects.append(other_pose.track_id)

            if len(enclosing_subjects) >= 3:
                # Mark target in distress
                interaction_predictions[target_pose.track_id] = BehaviorPrediction(
                    primary_behavior=BehaviorType.SURROUNDING,
                    confidence=0.88,
                    threat_level=ThreatLevel.HIGH,
                    threat_score=0.85,
                    reasoning=f"Enclosed and surrounded by a mob of {len(enclosing_subjects)} subjects",
                    interacting_with_track_id=enclosing_subjects[0],
                )
                for attacker_id in enclosing_subjects:
                    if attacker_id not in interaction_predictions:
                        interaction_predictions[attacker_id] = BehaviorPrediction(
                            primary_behavior=BehaviorType.SURROUNDING,
                            confidence=0.88,
                            threat_level=ThreatLevel.HIGH,
                            threat_score=0.85,
                            reasoning=f"Active participant in surrounding/mobbing target ID #{target_pose.track_id}",
                            interacting_with_track_id=target_pose.track_id,
                        )

    # Priority 2: Pairwise Dangerous Interactions (Fighting, Restraining, Snatching, Pursuit)
    for i in range(num_poses):
        pose_i = poses[i]
        tid_i = pose_i.track_id
        state_i = states_by_id.get(tid_i)
        if state_i is None:
            continue

        c_i = pose_i.bbox.centroid
        w_i = float(pose_i.bbox.width)
        h_i = float(pose_i.bbox.height)

        for j in range(i + 1, num_poses):
            pose_j = poses[j]
            tid_j = pose_j.track_id
            state_j = states_by_id.get(tid_j)
            if state_j is None:
                continue

            c_j = pose_j.bbox.centroid
            w_j = float(pose_j.bbox.width)
            h_j = float(pose_j.bbox.height)

            dist = math.hypot(c_i[0] - c_j[0], c_i[1] - c_j[1])
            avg_w = (w_i + w_j) / 2.0
            avg_h = (h_i + h_j) / 2.0
            box_iou = iou_xyxy(pose_i.bbox, pose_j.bbox)

            # Skip if one subject is already fallen (handled by post-assault fallen escalation)
            is_i_fallen = confirmed_behaviors_by_id.get(tid_i) == BehaviorType.FALLEN.value
            is_j_fallen = confirmed_behaviors_by_id.get(tid_j) == BehaviorType.FALLEN.value
            if is_i_fallen and is_j_fallen:
                continue

            # --- A. FIGHTING / VIOLENT CONFRONTATION ---
            is_close_combat = dist < (avg_w * fight_distance_norm)
            w_vel_i = state_i.wrist_velocity
            w_vel_j = state_j.wrist_velocity
            total_wrist_energy = w_vel_i + w_vel_j

            # Dual-assault or heavy asymmetric punching
            is_mutual_fight = is_close_combat and (
                total_wrist_energy > fight_wrist_energy_thresh
                or (w_vel_i > 750.0 and w_vel_j > 750.0)
            )
            is_asymmetric_assault = is_close_combat and (
                (w_vel_i > 950.0 and state_j.spine_angle > 25.0)
                or (w_vel_j > 950.0 and state_i.spine_angle > 25.0)
            )

            if is_mutual_fight or is_asymmetric_assault:
                interaction_predictions[tid_i] = BehaviorPrediction(
                    primary_behavior=BehaviorType.FIGHTING,
                    confidence=0.95,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.96,
                    reasoning=f"Violent physical confrontation / striking with ID #{tid_j} (wrist energy: {total_wrist_energy:.0f}px/s)",
                    interacting_with_track_id=tid_j,
                )
                interaction_predictions[tid_j] = BehaviorPrediction(
                    primary_behavior=BehaviorType.FIGHTING,
                    confidence=0.95,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.96,
                    reasoning=f"Violent physical confrontation / striking with ID #{tid_i} (wrist energy: {total_wrist_energy:.0f}px/s)",
                    interacting_with_track_id=tid_i,
                )
                continue

            # --- B. RESTRAINING / CHOKEHOLD / PHYSICAL GRAPPLING ---
            is_entangled = box_iou >= 0.38 or dist < (avg_w * 0.55)
            is_wrestling = (total_wrist_energy > 450.0) or (state_i.body_velocity < 200.0 and state_j.body_velocity < 200.0 and is_entangled)

            if is_entangled and is_wrestling:
                interaction_predictions[tid_i] = BehaviorPrediction(
                    primary_behavior=BehaviorType.RESTRAINING,
                    confidence=0.92,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.92,
                    reasoning=f"Close physical entanglement / chokehold / grappling with ID #{tid_j} (IoU: {box_iou:.2f})",
                    interacting_with_track_id=tid_j,
                )
                interaction_predictions[tid_j] = BehaviorPrediction(
                    primary_behavior=BehaviorType.RESTRAINING,
                    confidence=0.92,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.92,
                    reasoning=f"Close physical entanglement / victim restrained by ID #{tid_i} (IoU: {box_iou:.2f})",
                    interacting_with_track_id=tid_i,
                )
                continue

            # --- C. SNATCHING / ROBBERY (Close reach followed by rapid sprint divergence) ---
            spd_i = state_i.body_velocity / max(10.0, h_i)
            spd_j = state_j.body_velocity / max(10.0, h_j)

            # One subject sprinting at high speed while the other is slow/distressed
            if histories_by_id:
                h_list_i = histories_by_id.get(tid_i, [])
                h_list_j = histories_by_id.get(tid_j, [])
                if len(h_list_i) >= 6 and len(h_list_j) >= 6:
                    past_c_i = h_list_i[-6].centroid
                    past_c_j = h_list_j[-6].centroid
                    past_dist = math.hypot(past_c_i[0] - past_c_j[0], past_c_i[1] - past_c_j[1])

                    # Distance rapidly expanding (diverging) after being in close contact
                    dist_expansion_rate = (dist - past_dist) / max(1e-3, state_i.timestamp - h_list_i[-6].timestamp)
                    was_close = past_dist < (avg_w * 1.5)

                    if was_close and dist_expansion_rate > 220.0:
                        if spd_i > 1.8 and spd_j < 1.0:
                            interaction_predictions[tid_i] = BehaviorPrediction(
                                primary_behavior=BehaviorType.SNATCHING,
                                confidence=0.93,
                                threat_level=ThreatLevel.CRITICAL,
                                threat_score=0.94,
                                reasoning=f"Snatch-and-run / robbery sprint fleeing from victim ID #{tid_j} (divergence: {dist_expansion_rate:.0f}px/s)",
                                interacting_with_track_id=tid_j,
                            )
                            interaction_predictions[tid_j] = BehaviorPrediction(
                                primary_behavior=BehaviorType.HANDS_UP,
                                confidence=0.90,
                                threat_level=ThreatLevel.HIGH,
                                threat_score=0.80,
                                reasoning=f"Victim of snatching incident by fleeing suspect ID #{tid_i}",
                                interacting_with_track_id=tid_i,
                            )
                            continue
                        elif spd_j > 1.8 and spd_i < 1.0:
                            interaction_predictions[tid_j] = BehaviorPrediction(
                                primary_behavior=BehaviorType.SNATCHING,
                                confidence=0.93,
                                threat_level=ThreatLevel.CRITICAL,
                                threat_score=0.94,
                                reasoning=f"Snatch-and-run / robbery sprint fleeing from victim ID #{tid_i} (divergence: {dist_expansion_rate:.0f}px/s)",
                                interacting_with_track_id=tid_i,
                            )
                            interaction_predictions[tid_i] = BehaviorPrediction(
                                primary_behavior=BehaviorType.HANDS_UP,
                                confidence=0.90,
                                threat_level=ThreatLevel.HIGH,
                                threat_score=0.80,
                                reasoning=f"Victim of snatching incident by fleeing suspect ID #{tid_j}",
                                interacting_with_track_id=tid_j,
                            )
                            continue

            # --- D. PURSUIT / CHASING (Directionally aligned high-speed pursuit) ---
            both_running = spd_i >= 1.55 and spd_j >= 1.55
            in_chase_distance = (avg_h * 0.4) <= dist <= (avg_h * 4.5)
            cos_similarity = compute_vector_cosine_similarity(state_i.velocity_vector, state_j.velocity_vector)

            # High cosine similarity (>= 0.65) ensures they are running along the same trajectory
            if both_running and in_chase_distance and cos_similarity >= 0.65:
                interaction_predictions[tid_i] = BehaviorPrediction(
                    primary_behavior=BehaviorType.PURSUIT,
                    confidence=0.89,
                    threat_level=ThreatLevel.HIGH,
                    threat_score=0.88,
                    reasoning=f"High-speed pursuit / chase engagement with ID #{tid_j} (trajectory alignment: {cos_similarity:.2f})",
                    interacting_with_track_id=tid_j,
                )
                interaction_predictions[tid_j] = BehaviorPrediction(
                    primary_behavior=BehaviorType.PURSUIT,
                    confidence=0.89,
                    threat_level=ThreatLevel.HIGH,
                    threat_score=0.88,
                    reasoning=f"High-speed pursuit / chase engagement with ID #{tid_i} (trajectory alignment: {cos_similarity:.2f})",
                    interacting_with_track_id=tid_i,
                )
                continue

    return interaction_predictions
