"""ConfigManager — thread-safe JSON-backed configuration store.

Handles all CRUD operations on a JSON config file with atomic writes
and a threading.Lock for write safety across concurrent requests.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, Any] = {
    "immunefi_refresh_interval": 3600,
    "openai_model": "gpt-4o",
    "anthropic_model": "claude-3-5-sonnet-20241022",
    "max_concurrent_scans": 2,
    "max_concurrent_ai": 1,
    "priority_factors": {
        "bounty": 0.4,
        "similarity": 0.3,
        "chain": 0.15,
        "freshness": 0.1,
        "tp_history": 0.05,
    },
    "notification_channels": [],
    "rpc_endpoints": {
        "ethereum": "https://eth.llamarpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
    },
    "exploit_timeout_seconds": 300,
    "daemon_interval_minutes": 60,
}


class ConfigManager:
    """Thread-safe configuration manager backed by a JSON file.

    All write operations (set, delete, reset, bulk) acquire a threading.Lock
    to prevent races between concurrent requests. Reads are lock-free and
    operate on the in-memory dictionary.

    Attributes:
        data_dir: Directory where the config file is stored.
        config_file: Full path to the JSON config file.
    """

    def __init__(self, data_dir: str | Path = "/data/config") -> None:
        self._lock = threading.Lock()
        self._config: dict[str, Any] = {}
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "config.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """Load configuration from disk.

        If the config file does not exist, the default configuration is
        written to disk and returned.

        Returns:
            The loaded (or default) configuration dictionary.

        Raises:
            OSError: If the data directory cannot be created or the file
                     cannot be written.
        """
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            log.warning("config_data_dir_permission_denied", path=str(self.data_dir))
            return dict(DEFAULT_CONFIG)

        if not self.config_file.exists():
            log.info("config_file_not_found_creating_defaults", path=str(self.config_file))
            self._config = dict(DEFAULT_CONFIG)
            try:
                self._atomic_write()
            except PermissionError:
                log.warning("config_atomic_write_permission_denied")
            return dict(self._config)

        try:
            raw = self.config_file.read_text(encoding="utf-8")
            self._config = json.loads(raw)
            log.info("config_loaded", path=str(self.config_file), keys=len(self._config))
        except (json.JSONDecodeError, OSError) as exc:
            log.error("config_load_failed_falling_back_to_defaults", error=str(exc))
            self._config = dict(DEFAULT_CONFIG)
            try:
                self._atomic_write()
            except PermissionError:
                log.warning("config_atomic_write_permission_denied")

        return dict(self._config)

    def get(self, key: str) -> Any:
        """Retrieve a single configuration value.

        Args:
            key: The configuration key.

        Returns:
            The value associated with *key*, or ``None`` if the key does
            not exist.
        """
        return self._config.get(key)

    def get_all(self) -> dict[str, Any]:
        """Return the entire configuration dictionary.

        Returns:
            A shallow copy of the current in-memory configuration.
        """
        return dict(self._config)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration key and persist to disk.

        If the key already exists its value is overwritten.

        Args:
            key: The configuration key.
            value: The value to store (any JSON-serializable type).

        Raises:
            OSError: If the file cannot be written.
        """
        with self._lock:
            self._config[key] = value
            self._atomic_write()

    def delete(self, key: str) -> bool:
        """Delete a configuration key.

        Args:
            key: The configuration key to remove.

        Returns:
            ``True`` if the key existed and was removed, ``False`` if it
            did not exist.
        """
        with self._lock:
            if key not in self._config:
                return False
            del self._config[key]
            self._atomic_write()
            return True

    def reset(self) -> dict[str, Any]:
        """Restore the configuration to factory defaults.

        Returns:
            The default configuration dictionary.
        """
        with self._lock:
            self._config = dict(DEFAULT_CONFIG)
            self._atomic_write()
            log.info("config_reset_to_defaults")
        return dict(self._config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _atomic_write(self) -> None:
        """Write the current configuration to a temporary file, then
        atomically rename it over the target file.

        This prevents partial writes from corrupting the config file in
        the event of a crash or power loss during the write.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Use a temporary file in the same directory to guarantee the
        # rename is atomic (same filesystem).
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix="config_",
            dir=str(self.data_dir),
        )
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                json.dump(self._config, fh, indent=2, ensure_ascii=False)
                fh.flush()
                # Ensure data is flushed to disk for durability.
                # os.fsync is available on all platforms.
                os.fsync(fd)

            shutil.move(tmp_path, str(self.config_file))
        except Exception:
            # Clean up the temp file on failure.
            Path(tmp_path).unlink(missing_ok=True)
            raise

        log.debug("config_written_atomically", path=str(self.config_file))
