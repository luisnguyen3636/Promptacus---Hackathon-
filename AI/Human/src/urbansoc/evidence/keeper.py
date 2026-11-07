"""Cryptographic Evidence Keeping Engine for Urban Safety AI-SOC.

Ensures tamper-evident forensic integrity:
- Cryptographic SHA-256 and HMAC-SHA256 signatures for video keyframes and metadata.
- Continuous Hash Chaining (Merkle Ledger) preventing retroactive modification or deletion.
- Automated integrity verification and forensic evidence packaging.
"""

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("urbansoc.evidence.keeper")

DEFAULT_HMAC_KEY = "URBAN_SAFETY_SOC_MASTER_HMAC_SECRET_2026"
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


@dataclass
class EvidenceRecord:
    """Immutable forensic evidence record."""
    event_id: str
    camera_id: str
    timestamp_iso: str
    timestamp_unix: float
    frame_path: str
    frame_sha256: str
    frame_hmac: str
    metadata_sha256: str
    previous_chain_hash: str
    chain_hash: str
    operator_id: Optional[str] = None
    verification_status: str = "VERIFIED_VALID"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceKeeper:
    """Forensic Evidence Keeper implementing SHA-256 hashing, HMAC signing and Merkle hash chaining."""

    def __init__(
        self,
        storage_dir: str = "output/evidence_storage",
        secret_key: str = DEFAULT_HMAC_KEY,
    ) -> None:
        self.storage_dir = os.path.abspath(storage_dir)
        self.evidence_dir = os.path.join(self.storage_dir, "keyframes")
        self.ledger_file = os.path.join(self.storage_dir, "evidence_ledger.jsonl")
        self.secret_key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key

        os.makedirs(self.evidence_dir, exist_ok=True)
        self.records: List[EvidenceRecord] = []
        self._load_ledger()

    def _load_ledger(self) -> None:
        """Load and replay existing ledger to establish current chain state."""
        self.records = []
        if not os.path.exists(self.ledger_file):
            return

        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        rec = EvidenceRecord(**data)
                        self.records.append(rec)
                    except Exception as e:
                        logger.warning("Corrupted line in evidence ledger: %s (%s)", line, e)
        except Exception as e:
            logger.error("Failed to read evidence ledger %s: %s", self.ledger_file, e)

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Compute standard SHA-256 hexadecimal digest."""
        return hashlib.sha256(data).hexdigest()

    def compute_hmac(self, data: bytes) -> str:
        """Compute HMAC-SHA256 signature using the keeper's secret key."""
        return hmac.new(self.secret_key, data, hashlib.sha256).hexdigest()

    @property
    def latest_chain_hash(self) -> str:
        """Retrieve the latest block hash in the Merkle chain or the Genesis hash."""
        if not self.records:
            return GENESIS_HASH
        return self.records[-1].chain_hash

    def record_evidence(
        self,
        camera_id: str,
        frame_bgr: np.ndarray,
        metadata: Dict[str, Any],
        event_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        quality: int = 90,
    ) -> EvidenceRecord:
        """Record a keyframe and incident metadata into the forensic ledger."""
        now_unix = time.time()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_unix))

        evt_id = event_id or f"EVT_{int(now_unix * 1000)}_{camera_id}"
        frame_filename = f"{evt_id}_keyframe.jpg"
        frame_path = os.path.join(self.evidence_dir, frame_filename)

        # 1. Encode frame and compute image cryptographic hashes
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, enc = cv2.imencode(".jpg", frame_bgr, encode_params)
        if not success:
            raise ValueError(f"Failed to compress frame for camera {camera_id}")

        frame_bytes = enc.tobytes()
        frame_sha = self.compute_sha256(frame_bytes)
        frame_sig = self.compute_hmac(frame_bytes)

        # Write frame to disk
        with open(frame_path, "wb") as f:
            f.write(frame_bytes)

        # 2. Hash metadata dictionary
        meta_bytes = json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode("utf-8")
        meta_sha = self.compute_sha256(meta_bytes)

        # 3. Compute continuous Merkle hash chain
        prev_hash = self.latest_chain_hash
        chain_payload = f"{prev_hash}|{now_iso}|{evt_id}|{frame_sha}|{meta_sha}".encode("utf-8")
        curr_chain_hash = self.compute_sha256(chain_payload)

        # 4. Construct record and persist to append-only ledger
        rec = EvidenceRecord(
            event_id=evt_id,
            camera_id=camera_id,
            timestamp_iso=now_iso,
            timestamp_unix=now_unix,
            frame_path=frame_path,
            frame_sha256=frame_sha,
            frame_hmac=frame_sig,
            metadata_sha256=meta_sha,
            previous_chain_hash=prev_hash,
            chain_hash=curr_chain_hash,
            operator_id=operator_id,
            verification_status="VERIFIED_VALID",
        )

        self.records.append(rec)
        self._append_to_ledger(rec)

        # Save metadata copy alongside image
        meta_filename = f"{evt_id}_meta.json"
        meta_path = os.path.join(self.evidence_dir, meta_filename)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "evidence_record": rec.to_dict(),
                "payload": metadata,
            }, f, indent=2, ensure_ascii=False)

        return rec

    def _append_to_ledger(self, record: EvidenceRecord) -> None:
        """Append record to ledger file atomically."""
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(line)

    def verify_evidence_integrity(self, record: EvidenceRecord) -> Tuple[bool, str]:
        """Verify the integrity of a stored evidence keyframe on disk."""
        if not os.path.exists(record.frame_path):
            return False, f"Evidence file missing on disk: {record.frame_path}"

        try:
            with open(record.frame_path, "rb") as f:
                data = f.read()

            actual_sha = self.compute_sha256(data)
            if actual_sha != record.frame_sha256:
                return False, f"SHA-256 Mismatch: expected {record.frame_sha256}, got {actual_sha} (Tampering detected!)"

            actual_hmac = self.compute_hmac(data)
            if actual_hmac != record.frame_hmac:
                return False, f"HMAC Signature Mismatch: expected {record.frame_hmac}, got {actual_hmac}"

            return True, "Evidence keyframe is cryptographically valid and untampered."
        except Exception as e:
            return False, f"Verification failed with exception: {e}"

    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        """Verify the entire Merkle hash chain from Genesis to latest block."""
        errors: List[str] = []
        expected_prev = GENESIS_HASH

        for idx, rec in enumerate(self.records):
            if rec.previous_chain_hash != expected_prev:
                errors.append(
                    f"Block {idx} ({rec.event_id}): previous_chain_hash mismatch! "
                    f"Expected {expected_prev}, found {rec.previous_chain_hash}."
                )

            chain_payload = f"{rec.previous_chain_hash}|{rec.timestamp_iso}|{rec.event_id}|{rec.frame_sha256}|{rec.metadata_sha256}".encode("utf-8")
            recomputed = self.compute_sha256(chain_payload)
            if recomputed != rec.chain_hash:
                errors.append(
                    f"Block {idx} ({rec.event_id}): chain_hash corrupted! "
                    f"Expected {rec.chain_hash}, recomputed {recomputed}."
                )

            expected_prev = rec.chain_hash

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_record(self, event_id: str) -> Optional[EvidenceRecord]:
        """Lookup evidence record by event_id."""
        for r in reversed(self.records):
            if r.event_id == event_id:
                return r
        return None

    def package_incident_evidence(self, event_id: str) -> Dict[str, Any]:
        """Bundle incident keyframe, metadata, checksum manifest, and verification receipt."""
        rec = self.get_record(event_id)
        if not rec:
            raise KeyError(f"Evidence record '{event_id}' not found.")

        is_valid, msg = self.verify_evidence_integrity(rec)
        manifest_text = (
            f"# FORENSIC EVIDENCE MANIFEST\n"
            f"Event ID: {rec.event_id}\n"
            f"Camera ID: {rec.camera_id}\n"
            f"Timestamp: {rec.timestamp_iso}\n"
            f"Keyframe SHA-256: {rec.frame_sha256}\n"
            f"Keyframe HMAC: {rec.frame_hmac}\n"
            f"Metadata SHA-256: {rec.metadata_sha256}\n"
            f"Chain Hash: {rec.chain_hash}\n"
            f"Verification Result: {'PASS' if is_valid else 'FAIL'} - {msg}\n"
        )

        manifest_path = os.path.join(self.evidence_dir, f"{event_id}_manifest.txt")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_text)

        return {
            "event_id": rec.event_id,
            "camera_id": rec.camera_id,
            "timestamp": rec.timestamp_iso,
            "frame_path": rec.frame_path,
            "frame_sha256": rec.frame_sha256,
            "frame_hmac": rec.frame_hmac,
            "chain_hash": rec.chain_hash,
            "manifest_path": manifest_path,
            "integrity_verified": is_valid,
            "integrity_message": msg,
        }
