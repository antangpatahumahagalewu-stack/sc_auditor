"""Dependency resolver for Solidity source code.

Resolves import statements (``import "..."``) by locating dependencies
in standard locations (``node_modules/``, ``lib/``, ``./``) or by
downloading them from GitHub when they match known patterns like
OpenZeppelin.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()

# Known dependency prefixes that map to GitHub repositories.
KNOWN_DEPENDENCIES: dict[str, str] = {
    "@openzeppelin": "https://github.com/OpenZeppelin/openzeppelin-contracts",
    "@uniswap": "https://github.com/Uniswap/v3-core",
    "@chainlink": "https://github.com/smartcontractkit/chainlink",
    "@aave": "https://github.com/aave/protocol-v2",
    "@solmate": "https://github.com/transmissions11/solmate",
    "@solady": "https://github.com/Vectorized/solady",
    "@prb/math": "https://github.com/PaulRBerg/prb-math",
    "@mud": "https://github.com/latticexyz/mud",
}

# Compile-on-demand version for each known dependency.
DEPENDENCY_REF: dict[str, str] = {
    "@openzeppelin": "v5.0.2",
    "@uniswap": "v3.0.0",
    "@chainlink": "v2.10.0",
    "@aave": "v2.0.0",
    "@solmate": "v6.7.0",
    "@solady": "v0.0.182",
    "@prb/math": "v4.0.0",
}


class DependencyResolver:
    """Resolve Solidity import dependencies.

    Looks for imports in the following order:
      1. Local project relative paths
      2. ``node_modules/`` (npm-style)
      3. ``lib/`` (forge-style)
      4. GitHub download (for known packages)

    Args:
        working_dir: Working directory for downloaded dependencies.
        github_token: Optional GitHub token for API access.
    """

    def __init__(
        self,
        working_dir: str | Path = "/data/scanner",
        github_token: str | None = None,
    ) -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)
        self._deps_dir = self._working_dir / "deps"
        self._deps_dir.mkdir(parents=True, exist_ok=True)
        self._github_token = github_token or os.getenv("GITHUB_TOKEN")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        source_dir: str | Path,
        imports: list[str] | None = None,
    ) -> dict[str, str]:
        """Resolve all dependencies for contracts in ``source_dir``.

        Scans ``.sol`` files for import statements and resolves them.
        Returns a mapping of import path → resolved file path.

        Args:
            source_dir: Directory containing Solidity files.
            imports: Explicit list of imports to resolve. If ``None``,
                     all imports in the source tree are scanned.

        Returns:
            Dict mapping resolved import paths to absolute file paths
            on the local filesystem.
        """
        source_path = Path(source_dir)
        resolved: dict[str, str] = {}

        if not source_path.is_dir():
            log.warning("deps.source_dir_not_found", path=str(source_path))
            return resolved

        # Collect imports if not provided
        if imports is None:
            imports = self._scan_imports(source_path)

        if not imports:
            return resolved

        for imp in imports:
            file_path = self._resolve_single(source_path, imp)
            if file_path:
                resolved[imp] = str(file_path)

        log.info(
            "deps.resolve_complete",
            total_imports=len(imports),
            resolved=len(resolved),
        )

        return resolved

    def install_forge_deps(self, source_dir: str | Path) -> bool:
        """Run ``forge install`` to fetch dependencies for a Foundry project.

        This is the preferred method for Foundry-based projects as it
        respects ``remappings.txt`` and ``foundry.toml``.

        Args:
            source_dir: Directory containing a Foundry project.

        Returns:
            ``True`` if installation succeeded.
        """
        source_path = Path(source_dir)

        if not (source_path / "foundry.toml").exists():
            log.debug("deps.no_foundry_toml", path=str(source_path))
            return False

        log.info("deps.running_forge_install", path=str(source_path))

        try:
            result = subprocess.run(
                ["forge", "install"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(source_path),
            )
            if result.returncode == 0:
                log.info("deps.forge_install_success")
                return True
            log.warning(
                "deps.forge_install_failed",
                stderr=result.stderr.strip()[:500],
            )
            return False
        except FileNotFoundError:
            log.warning("deps.forge_not_found")
            return False
        except subprocess.TimeoutExpired:
            log.warning("deps.forge_install_timeout")
            return False
        except OSError as exc:
            log.warning("deps.forge_install_os_error", error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_single(
        self,
        source_dir: Path,
        import_path: str,
    ) -> str | None:
        """Resolve a single import path to a local file."""
        # 1. Local relative path
        local = source_dir / import_path
        if local.exists() and local.is_file():
            return str(local.resolve())

        # 2. node_modules/ (npm-style)
        node_modules_path = self._find_in_node_modules(source_dir, import_path)
        if node_modules_path:
            return node_modules_path

        # 3. lib/ (forge-style)
        lib_path = self._find_in_lib(source_dir, import_path)
        if lib_path:
            return lib_path

        # 4. Known dependency — download from GitHub
        github_path = self._resolve_github_dep(import_path)
        if github_path:
            return github_path

        log.debug("deps.unresolved_import", import_path=import_path)
        return None

    @staticmethod
    def _scan_imports(source_dir: Path) -> list[str]:
        """Scan all ``.sol`` files for import statements."""
        imports: list[str] = []
        import_pattern = re.compile(
            r'import\s+(?:\{[^}]*\}\s+from\s+)?["\']([^"\']+)["\']\s*;'
        )

        sol_files = list(source_dir.rglob("*.sol"))
        for sol_file in sol_files:
            try:
                content = sol_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for match in import_pattern.finditer(content):
                imported_path = match.group(1)
                # Skip solidity built-ins
                if imported_path.startswith("hardhat/") or imported_path in (
                    "ds-test/test.sol",
                    "forge-std/Test.sol",
                ):
                    continue
                if imported_path not in imports:
                    imports.append(imported_path)

        return imports

    @staticmethod
    def _find_in_node_modules(
        source_dir: Path,
        import_path: str,
    ) -> str | None:
        """Search for an import in ``node_modules/``."""
        # Walk up the directory tree looking for node_modules
        current = source_dir.resolve()
        for _ in range(10):  # max depth
            nm = current / "node_modules"
            target = nm / import_path
            if target.exists() and target.is_file():
                return str(target.resolve())
            parent = current.parent
            if parent == current:
                break
            current = parent

        # Also check standard node_modules locations
        candidates = [
            source_dir / "node_modules" / import_path,
            source_dir.parent / "node_modules" / import_path,
        ]
        for c in candidates:
            resolved = c.resolve()
            if resolved.exists() and resolved.is_file():
                return str(resolved)

        return None

    @staticmethod
    def _find_in_lib(
        source_dir: Path,
        import_path: str,
    ) -> str | None:
        """Search for an import in ``lib/`` (forge-style)."""
        # Common forge directory structure:
        # project/
        #   lib/
        #     openzeppelin-contracts/
        #       contracts/
        #         token/ERC20.sol
        # Import might be: "@openzeppelin/contracts/token/ERC20.sol"
        # Resides in:      lib/openzeppelin-contracts/contracts/token/ERC20.sol

        lib_dir = source_dir / "lib"
        if not lib_dir.is_dir():
            return None

        # Try to use remappings.txt if present
        remappings = source_dir / "remappings.txt"
        if remappings.exists():
            try:
                for line in remappings.read_text().splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    if "=" in stripped:
                        prefix, target = stripped.split("=", 1)
                        if import_path.startswith(prefix):
                            relative = import_path[len(prefix):]
                            candidate = lib_dir / target.strip() / relative
                            candidate = candidate.resolve()
                            if candidate.exists() and candidate.is_file():
                                return str(candidate)
            except OSError:
                pass

        # Without remappings, try by stripping @scope/ prefix
        if import_path.startswith("@"):
            # e.g. "@openzeppelin/contracts/token.sol"
            # -> lib/openzeppelin-contracts/contracts/token.sol
            parts = import_path.split("/", 2)
            if len(parts) >= 2:
                scope = parts[0].lstrip("@")
                # Common pattern: @openzeppelin -> openzeppelin-contracts
                lib_candidates = [
                    lib_dir / f"{scope}-contracts" / "/".join(parts[1:]),
                    lib_dir / scope / "/".join(parts[1:]),
                    lib_dir / import_path,
                ]
                for c in lib_candidates:
                    resolved = c.resolve()
                    if resolved.exists() and resolved.is_file():
                        return str(resolved)

        # Direct match in lib
        direct = (lib_dir / import_path).resolve()
        if direct.exists() and direct.is_file():
            return str(direct)

        return None

    def _resolve_github_dep(self, import_path: str) -> str | None:
        """Download a dependency from GitHub if it is a known package."""
        # Check if import starts with a known dependency prefix
        matched_prefix = None
        for prefix in KNOWN_DEPENDENCIES:
            if import_path.startswith(prefix):
                matched_prefix = prefix
                break

        if not matched_prefix:
            return None

        # Already downloaded?
        local_dep = self._deps_dir / matched_prefix.lstrip("@")
        relative_path = import_path[len(matched_prefix):].lstrip("/")

        target_file = (local_dep / relative_path).resolve()
        if target_file.exists() and target_file.is_file():
            return str(target_file)

        # Download from GitHub
        repo_url = KNOWN_DEPENDENCIES[matched_prefix]
        ref = DEPENDENCY_REF.get(matched_prefix, "master")
        success = self._download_github_dep(repo_url, ref, local_dep)

        if success:
            target_file = (local_dep / relative_path).resolve()
            if target_file.exists() and target_file.is_file():
                return str(target_file)

        # Try to find the file within the downloaded directory
        if success and local_dep.exists():
            # Search recursively
            for f in local_dep.rglob("*.sol"):
                if f.name == Path(import_path).name:
                    return str(f.resolve())

            # If the subpath after the prefix matches a real path
            search = local_dep / relative_path
            if search.exists():
                return str(search.resolve())

        return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _download_github_dep(
        self,
        repo_url: str,
        ref: str,
        target_dir: Path,
    ) -> bool:
        """Download a dependency from GitHub using git clone --depth=1.

        Uses tenacity for automatic retries on network failures.
        """
        log.info("deps.downloading", repo=repo_url, ref=ref, target=str(target_dir))

        # Clean up any partial downloads
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        try:
            result = subprocess.run(
                [
                    "git", "clone", "--depth=1",
                    "--branch", ref,
                    repo_url,
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                log.info("deps.download_success", repo=repo_url)
                return True

            log.warning(
                "deps.download_failed",
                repo=repo_url,
                stderr=result.stderr.strip()[:500],
            )
            return False

        except (subprocess.TimeoutExpired, OSError) as exc:
            log.error("deps.download_error", repo=repo_url, error=str(exc))
            return False


# ------------------------------------------------------------------
# Convenience factory
# ------------------------------------------------------------------

def create_dependency_resolver(
    working_dir: str | Path = "/data/scanner",
) -> DependencyResolver:
    """Create a configured ``DependencyResolver`` instance."""
    return DependencyResolver(working_dir=working_dir)
