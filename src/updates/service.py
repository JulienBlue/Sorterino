"""GitHub release based updater with strict origin and integrity checks."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request

from src.version import APP_VERSION


REPOSITORY = "JulienBlue/Sorterino"
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
MAX_API_BYTES = 2 * 1024 * 1024
MAX_CHECKSUM_BYTES = 64 * 1024
MAX_INSTALLER_BYTES = 1024 * 1024 * 1024
NETWORK_TIMEOUT_SECONDS = 20
DOWNLOAD_TIMEOUT_SECONDS = 60
_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:(?P<stage>alpha|a|beta|b|rc)(?P<stage_number>\d*))?$",
    re.IGNORECASE,
)
_INSTALLER_PATTERN = re.compile(r"^Sorterino_Setup_v?[0-9A-Za-z.\-]+\.exe$")
_SHA256_PATTERN = re.compile(r"\b([0-9a-fA-F]{64})\b")


class UpdateError(RuntimeError):
    """An update cannot safely be checked, downloaded, or launched."""


@dataclass(frozen=True, order=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    stage_rank: int
    stage_number: int


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int
    digest: str | None = None


@dataclass(frozen=True)
class UpdateRelease:
    version: str
    tag_name: str
    prerelease: bool
    notes: str
    page_url: str
    published_at: str
    installer: ReleaseAsset
    checksum_asset: ReleaseAsset | None = None

    @property
    def has_integrity_information(self) -> bool:
        return bool(self.installer.digest or self.checksum_asset)


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    release: UpdateRelease | None

    @property
    def update_available(self) -> bool:
        return self.release is not None


def parse_version(value: str) -> ParsedVersion:
    match = _VERSION_PATTERN.fullmatch(str(value or "").strip())
    if not match:
        raise ValueError(f"Ungültige Versionsnummer: {value!r}")
    stage = (match.group("stage") or "stable").lower()
    stage_rank = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2, "stable": 3}[stage]
    return ParsedVersion(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch") or 0),
        stage_rank,
        int(match.group("stage_number") or 0),
    )


def normalize_version(value: str) -> str:
    return str(value or "").strip().removeprefix("v")


def _allowed_download_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host == "github.com"
        or host == "api.github.com"
        or host.endswith(".githubusercontent.com")
    )


class UpdateService:
    """Check and stage updates without modifying the running installation."""

    def __init__(
        self,
        current_version: str = APP_VERSION,
        urlopen: Callable = urllib.request.urlopen,
    ):
        self.current_version = current_version
        self._urlopen = urlopen

    @staticmethod
    def _request(url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"Sorterino/{APP_VERSION}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def _read_limited(self, response, limit: int) -> bytes:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise UpdateError("Die Serverantwort überschreitet die zulässige Größe.")
        return data

    def _open(self, url: str, timeout: int):
        if not _allowed_download_url(url):
            raise UpdateError("Die Updateadresse gehört nicht zu einer erlaubten GitHub-Domain.")
        try:
            response = self._urlopen(self._request(url), timeout=timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise UpdateError("Der GitHub-Updatedienst ist momentan nicht erreichbar.") from exc
        final_url = getattr(response, "geturl", lambda: url)()
        if not _allowed_download_url(final_url):
            response.close()
            raise UpdateError("GitHub hat den Download auf eine nicht erlaubte Domain umgeleitet.")
        return response

    def check(self, channel: str = "beta") -> UpdateCheckResult:
        try:
            with self._open(RELEASES_API, NETWORK_TIMEOUT_SECONDS) as response:
                payload = json.loads(self._read_limited(response, MAX_API_BYTES).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise UpdateError("GitHub hat ungültige Releasedaten geliefert.") from exc
        if not isinstance(payload, list):
            raise UpdateError("GitHub hat ein unerwartetes Releaseformat geliefert.")

        current = parse_version(self.current_version)
        candidates: list[tuple[ParsedVersion, UpdateRelease]] = []
        for item in payload:
            release = self._parse_release(item, channel)
            if release is None:
                continue
            try:
                parsed = parse_version(release.version)
            except ValueError:
                continue
            if parsed > current:
                candidates.append((parsed, release))
        candidates.sort(key=lambda entry: entry[0], reverse=True)
        return UpdateCheckResult(
            current_version=self.current_version,
            release=candidates[0][1] if candidates else None,
        )

    def _parse_release(self, item, channel: str) -> UpdateRelease | None:
        if not isinstance(item, dict) or item.get("draft"):
            return None
        prerelease = bool(item.get("prerelease"))
        tag_name = str(item.get("tag_name") or "").strip()
        version = normalize_version(tag_name)
        try:
            parsed = parse_version(version)
        except ValueError:
            return None
        if str(channel).casefold() == "stable" and (prerelease or parsed.stage_rank < 3):
            return None

        assets = [self._parse_asset(asset) for asset in (item.get("assets") or [])]
        assets = [asset for asset in assets if asset is not None]
        expected_installer_names = {
            f"Sorterino_Setup_v{version}.exe",
            f"Sorterino_Setup_{version}.exe",
        }
        installer = next(
            (
                asset for asset in assets
                if _INSTALLER_PATTERN.fullmatch(asset.name)
                and asset.name in expected_installer_names
            ),
            None,
        )
        if installer is None:
            return None
        checksum_asset = next(
            (asset for asset in assets if asset.name == f"{installer.name}.sha256"),
            None,
        )
        return UpdateRelease(
            version=version,
            tag_name=tag_name,
            prerelease=prerelease,
            notes=str(item.get("body") or "").strip(),
            page_url=str(item.get("html_url") or ""),
            published_at=str(item.get("published_at") or ""),
            installer=installer,
            checksum_asset=checksum_asset,
        )

    @staticmethod
    def _parse_asset(item) -> ReleaseAsset | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name") or "")
        url = str(item.get("browser_download_url") or "")
        if not name or Path(name).name != name or not _allowed_download_url(url):
            return None
        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            return None
        digest = str(item.get("digest") or "").strip() or None
        return ReleaseAsset(name=name, download_url=url, size=size, digest=digest)

    def _expected_digest(self, release: UpdateRelease) -> str:
        digest = release.installer.digest or ""
        if digest.lower().startswith("sha256:"):
            candidate = digest.split(":", 1)[1].strip()
            if re.fullmatch(r"[0-9a-fA-F]{64}", candidate):
                return candidate.lower()
        if release.checksum_asset:
            with self._open(release.checksum_asset.download_url, NETWORK_TIMEOUT_SECONDS) as response:
                text = self._read_limited(response, MAX_CHECKSUM_BYTES).decode("ascii", errors="strict")
            for line in text.splitlines():
                if release.installer.name in line or len(text.splitlines()) == 1:
                    match = _SHA256_PATTERN.search(line)
                    if match:
                        return match.group(1).lower()
        raise UpdateError(
            "Dieses Release enthält keine überprüfbare SHA-256-Prüfsumme und wird nicht installiert."
        )

    def download(
        self,
        release: UpdateRelease,
        destination_root: Path,
        progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        asset = release.installer
        if not _INSTALLER_PATTERN.fullmatch(asset.name) or Path(asset.name).name != asset.name:
            raise UpdateError("Der Installername ist ungültig.")
        if asset.size <= 0 or asset.size > MAX_INSTALLER_BYTES:
            raise UpdateError("Die angegebene Installergröße ist ungültig.")
        expected_digest = self._expected_digest(release)
        destination = Path(destination_root) / release.version / asset.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and self._hash_file(destination) == expected_digest:
            return destination

        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{asset.name}.",
                suffix=".part",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                digest = sha256()
                downloaded = 0
                with self._open(asset.download_url, DOWNLOAD_TIMEOUT_SECONDS) as response:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > MAX_INSTALLER_BYTES or downloaded > asset.size:
                            raise UpdateError("Der Download ist größer als von GitHub angegeben.")
                        handle.write(chunk)
                        digest.update(chunk)
                        if progress:
                            progress(downloaded, asset.size)
                handle.flush()
                os.fsync(handle.fileno())
            if downloaded != asset.size:
                raise UpdateError("Der Installer wurde nicht vollständig heruntergeladen.")
            if digest.hexdigest().lower() != expected_digest:
                raise UpdateError("Die SHA-256-Prüfsumme des Installers stimmt nicht überein.")
            temporary.replace(destination)
            temporary = None
            return destination
        finally:
            if temporary and temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower()


def launch_installer_after_exit(installer: Path, parent_pid: int | None = None) -> None:
    """Start a trusted local installer only after the current process exits."""
    installer = Path(installer).resolve()
    if os.name != "nt" or not installer.is_file():
        raise UpdateError("Der Installer kann auf diesem System nicht gestartet werden.")
    powershell = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell.is_file():
        raise UpdateError("Windows PowerShell wurde nicht gefunden.")
    process_id = int(parent_pid or os.getpid())
    launch_log = installer.parent / "update-launch.log"
    try:
        with open(launch_log, "a", encoding="utf-8") as handle:
            handle.write(
                f"Update angefordert: PID {process_id}, Installer {installer.name}\n"
            )
    except OSError as exc:
        raise UpdateError("Das Update-Protokoll konnte nicht angelegt werden.") from exc
    # Pass dynamic values through the child-only environment. Positional
    # values following PowerShell's -Command are not bound consistently when
    # paths contain spaces or non-ASCII characters. EncodedCommand avoids the
    # command-line quoting and injection problem altogether.
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "try {\n"
        "  $parent = [int]$env:SORTERINO_UPDATE_PARENT_PID\n"
        "  $installer = $env:SORTERINO_UPDATE_INSTALLER\n"
        "  $log = $env:SORTERINO_UPDATE_LOG\n"
        "  [IO.File]::AppendAllText($log, ('{0:u} Starter aktiv' -f [DateTime]::Now) + [Environment]::NewLine)\n"
        "  $deadline = [DateTime]::UtcNow.AddSeconds(45)\n"
        "  while ((Get-Process -Id $parent -ErrorAction SilentlyContinue) -and "
        "         ([DateTime]::UtcNow -lt $deadline)) { Start-Sleep -Milliseconds 250 }\n"
        "  if (Get-Process -Id $parent -ErrorAction SilentlyContinue) {\n"
        "    throw 'Sorterino wurde nicht innerhalb von 45 Sekunden beendet.'\n"
        "  }\n"
        "  Start-Sleep -Milliseconds 1200\n"
        "  if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {\n"
        "    throw 'Der heruntergeladene Installer wurde nicht gefunden.'\n"
        "  }\n"
        "  $process = Start-Process -FilePath $installer -ArgumentList '/CLOSEAPPLICATIONS','/NORESTART' -PassThru\n"
        "  [IO.File]::AppendAllText($log, ('{0:u} Installer gestartet, PID {1}' -f [DateTime]::Now, $process.Id) + [Environment]::NewLine)\n"
        "} catch {\n"
        "  $message = ('{0:u} {1}' -f [DateTime]::Now, $_.Exception.Message)\n"
        "  [IO.File]::AppendAllText($log, $message + [Environment]::NewLine)\n"
        "  exit 1\n"
        "}\n"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    child_environment = os.environ.copy()
    child_environment.update(
        {
            "SORTERINO_UPDATE_PARENT_PID": str(process_id),
            "SORTERINO_UPDATE_INSTALLER": str(installer),
            "SORTERINO_UPDATE_LOG": str(launch_log),
        }
    )
    # DETACHED_PROCESS prevented PowerShell from reaching the script on some
    # Windows installations. CREATE_NO_WINDOW keeps the helper invisible;
    # CREATE_NEW_PROCESS_GROUP lets it continue independently after Sorterino
    # exits.
    creation_flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(
        [
            str(powershell),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        cwd=str(installer.parent),
        env=child_environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
        startupinfo=startup_info,
    )
