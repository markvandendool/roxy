#!/usr/bin/env python3
"""
Rocky IPC - Shared Memory Brain
Story: RAF-010
Target: 79GB available, 1GB pre-allocated, <1μs IPC latency

Uses POSIX shared memory via mmap for zero-copy IPC between ROXY components.
"""

import mmap
import os
import struct
import time
import json
from dataclasses import dataclass
from typing import Optional, Any
import threading

# Shared memory configuration
SHM_NAME = "/roxy_brain"
SHM_PATH = "/dev/shm/roxy_brain"
SHM_SIZE = 1024 * 1024 * 1024  # 1GB pre-allocated
HEADER_SIZE = 4096  # Reserved for metadata

# Message format
MSG_HEADER_SIZE = 16  # 4 bytes type + 4 bytes length + 8 bytes timestamp


@dataclass
class ShmMessage:
    """Message in shared memory."""
    msg_type: int
    payload: bytes
    timestamp: float


class RoxyShmBrain:
    """
    Shared memory IPC hub for ROXY components.

    Memory Layout:
    [0-4095]     : Header (version, write_pos, read_pos, flags)
    [4096-...]   : Ring buffer for messages
    """

    # Message types
    MSG_PING = 1
    MSG_PONG = 2
    MSG_PITCH = 10
    MSG_CHORD = 11
    MSG_COMMAND = 20
    MSG_RESPONSE = 21
    MSG_STATE = 30

    VERSION = 1

    def __init__(self, create: bool = False, size: int = SHM_SIZE):
        self.size = size
        self.shm_fd = None
        self.mm = None
        self.lock = threading.Lock()

        if create:
            self._create_shm()
        else:
            self._open_shm()

        print(f"[ROXY.SHM] Brain {'created' if create else 'attached'}: {size // (1024*1024)}MB")

    def _create_shm(self):
        """Create and initialize shared memory."""
        # Remove existing if present
        if os.path.exists(SHM_PATH):
            os.unlink(SHM_PATH)

        # Create file
        self.shm_fd = os.open(
            SHM_PATH,
            os.O_CREAT | os.O_RDWR,
            0o666
        )

        # Set size
        os.ftruncate(self.shm_fd, self.size)

        # Map memory
        self.mm = mmap.mmap(
            self.shm_fd,
            self.size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )

        # Initialize header
        self._write_header(
            version=self.VERSION,
            write_pos=HEADER_SIZE,
            read_pos=HEADER_SIZE,
            flags=0,
        )

    def _open_shm(self):
        """Open existing shared memory."""
        if not os.path.exists(SHM_PATH):
            raise FileNotFoundError(f"Shared memory not found: {SHM_PATH}")

        self.shm_fd = os.open(SHM_PATH, os.O_RDWR)

        # Get actual size
        stat = os.fstat(self.shm_fd)
        self.size = stat.st_size

        self.mm = mmap.mmap(
            self.shm_fd,
            self.size,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
        )

        # Verify header
        header = self._read_header()
        if header["version"] != self.VERSION:
            raise ValueError(f"Version mismatch: {header['version']} != {self.VERSION}")

    def _write_header(self, version: int, write_pos: int, read_pos: int, flags: int):
        """Write header to shared memory."""
        header = struct.pack("<IIII", version, write_pos, read_pos, flags)
        self.mm[0:16] = header

    def _read_header(self) -> dict:
        """Read header from shared memory."""
        header_bytes = self.mm[0:16]
        version, write_pos, read_pos, flags = struct.unpack("<IIII", header_bytes)
        return {
            "version": version,
            "write_pos": write_pos,
            "read_pos": read_pos,
            "flags": flags,
        }

    def _update_write_pos(self, new_pos: int):
        """Update write position atomically."""
        struct.pack_into("<I", self.mm, 4, new_pos)

    def _update_read_pos(self, new_pos: int):
        """Update read position atomically."""
        struct.pack_into("<I", self.mm, 8, new_pos)

    def write(self, msg_type: int, payload: bytes) -> bool:
        """
        Write message to shared memory.

        Returns True if successful, False if buffer full.
        """
        with self.lock:
            header = self._read_header()
            write_pos = header["write_pos"]

            # Calculate total message size
            msg_size = MSG_HEADER_SIZE + len(payload)

            # Check if we have space (simple linear buffer for now)
            if write_pos + msg_size > self.size:
                # Wrap around
                write_pos = HEADER_SIZE

            # Write message header
            timestamp = time.time()
            msg_header = struct.pack("<IId", msg_type, len(payload), timestamp)
            self.mm[write_pos:write_pos + MSG_HEADER_SIZE] = msg_header

            # Write payload
            payload_start = write_pos + MSG_HEADER_SIZE
            self.mm[payload_start:payload_start + len(payload)] = payload

            # Update write position
            new_write_pos = write_pos + msg_size
            self._update_write_pos(new_write_pos)

            return True

    def read(self, timeout_ms: int = 0) -> Optional[ShmMessage]:
        """
        Read next message from shared memory.

        Returns None if no message available within timeout.
        """
        start = time.perf_counter()

        while True:
            with self.lock:
                header = self._read_header()
                read_pos = header["read_pos"]
                write_pos = header["write_pos"]

                if read_pos != write_pos:
                    # Message available
                    msg_header = self.mm[read_pos:read_pos + MSG_HEADER_SIZE]
                    msg_type, payload_len, timestamp = struct.unpack("<IId", msg_header)

                    payload_start = read_pos + MSG_HEADER_SIZE
                    payload = bytes(self.mm[payload_start:payload_start + payload_len])

                    # Update read position
                    new_read_pos = read_pos + MSG_HEADER_SIZE + payload_len
                    if new_read_pos >= self.size - HEADER_SIZE:
                        new_read_pos = HEADER_SIZE
                    self._update_read_pos(new_read_pos)

                    return ShmMessage(
                        msg_type=msg_type,
                        payload=payload,
                        timestamp=timestamp,
                    )

            # Check timeout
            if timeout_ms == 0:
                return None

            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms >= timeout_ms:
                return None

            # Brief sleep
            time.sleep(0.0001)  # 100μs

    def write_json(self, msg_type: int, data: Any) -> bool:
        """Write JSON-serializable data."""
        payload = json.dumps(data).encode("utf-8")
        return self.write(msg_type, payload)

    def read_json(self, timeout_ms: int = 0) -> Optional[tuple]:
        """Read message and parse payload as JSON."""
        msg = self.read(timeout_ms)
        if msg is None:
            return None

        try:
            data = json.loads(msg.payload.decode("utf-8"))
            return (msg.msg_type, data, msg.timestamp)
        except json.JSONDecodeError:
            return (msg.msg_type, msg.payload, msg.timestamp)

    def ping(self) -> float:
        """Send ping and measure round-trip time."""
        start = time.perf_counter()
        self.write(self.MSG_PING, b"ping")

        # Wait for pong
        while True:
            msg = self.read(timeout_ms=1000)
            if msg and msg.msg_type == self.MSG_PONG:
                break

        return (time.perf_counter() - start) * 1_000_000  # microseconds

    def cleanup(self):
        """Clean up shared memory."""
        if self.mm:
            self.mm.close()
        if self.shm_fd:
            os.close(self.shm_fd)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()


def run_server():
    """Run as server (creates shm)."""
    print("[ROXY.SHM] Starting brain server...")

    with RoxyShmBrain(create=True) as brain:
        print(f"[ROXY.SHM] Brain ready at {SHM_PATH}")
        print("[ROXY.SHM] Waiting for messages (Ctrl+C to stop)...")

        try:
            while True:
                msg = brain.read(timeout_ms=100)
                if msg:
                    if msg.msg_type == brain.MSG_PING:
                        brain.write(brain.MSG_PONG, b"pong")
                        print(f"[ROXY.SHM] Ping-pong")
                    else:
                        print(f"[ROXY.SHM] Received: type={msg.msg_type}, "
                              f"len={len(msg.payload)}")
        except KeyboardInterrupt:
            print("\n[ROXY.SHM] Shutting down...")


def run_client():
    """Run as client (attaches to existing shm)."""
    print("[ROXY.SHM] Connecting to brain...")

    with RoxyShmBrain(create=False) as brain:
        # Measure latency
        latencies = []
        for _ in range(100):
            lat = brain.ping()
            latencies.append(lat)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)

        print(f"[ROXY.SHM] IPC Latency: avg={avg_lat:.2f}μs, "
              f"min={min_lat:.2f}μs, max={max_lat:.2f}μs")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client()
    else:
        run_server()
