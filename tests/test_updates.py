import io
import json
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from src.updates.service import (
    UpdateError,
    UpdateService,
    launch_installer_after_exit,
    parse_version,
)
from tools.create_release_checksum import create_checksum


class FakeResponse(io.BytesIO):
    def __init__(self, payload, url="https://api.github.com/repos/JulienBlue/Sorterino/releases"):
        super().__init__(payload)
        self._url = url

    def geturl(self):
        return self._url


def release_payload(version, *, prerelease=True, digest=None, checksum=False):
    installer_name = f"Sorterino_Setup_v{version}.exe"
    assets = [{
        "name": installer_name,
        "browser_download_url": f"https://github.com/JulienBlue/Sorterino/releases/download/v{version}/{installer_name}",
        "size": 4,
        "digest": digest,
    }]
    if checksum:
        assets.append({
            "name": f"{installer_name}.sha256",
            "browser_download_url": f"https://github.com/JulienBlue/Sorterino/releases/download/v{version}/{installer_name}.sha256",
            "size": 100,
        })
    return {
        "draft": False,
        "prerelease": prerelease,
        "tag_name": f"v{version}",
        "body": "Änderungen",
        "html_url": f"https://github.com/JulienBlue/Sorterino/releases/tag/v{version}",
        "published_at": "2026-09-26T12:00:00Z",
        "assets": assets,
    }


class UpdateTests(unittest.TestCase):
    def test_version_order_handles_beta_rc_and_stable(self):
        self.assertLess(parse_version("2.1beta"), parse_version("2.1rc1"))
        self.assertLess(parse_version("2.1rc1"), parse_version("2.1"))
        self.assertLess(parse_version("2.1"), parse_version("2.2beta"))
        self.assertLess(parse_version("2.2beta"), parse_version("2.2beta1"))

    def test_beta_channel_finds_newest_release(self):
        payload = json.dumps([
            release_payload("2.3beta", digest="sha256:" + "a" * 64),
            release_payload("2.1", prerelease=False, digest="sha256:" + "b" * 64),
        ]).encode()
        service = UpdateService(urlopen=lambda *_args, **_kwargs: FakeResponse(payload))
        result = service.check("beta")
        self.assertEqual(result.release.version, "2.3beta")

    def test_stable_channel_ignores_prerelease(self):
        payload = json.dumps([
            release_payload("2.3beta", digest="sha256:" + "a" * 64),
            release_payload("2.2", prerelease=False, digest="sha256:" + "b" * 64),
        ]).encode()
        service = UpdateService(urlopen=lambda *_args, **_kwargs: FakeResponse(payload))
        result = service.check("stable")
        self.assertEqual(result.release.version, "2.2")

    def test_release_without_checksum_is_visible_but_not_installable(self):
        payload = json.dumps([release_payload("2.3beta")]).encode()
        service = UpdateService(urlopen=lambda *_args, **_kwargs: FakeResponse(payload))
        release = service.check("beta").release
        self.assertFalse(release.has_integrity_information)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(UpdateError):
                service.download(release, Path(temp))

    def test_download_requires_matching_digest(self):
        installer = b"test"
        payload = json.dumps([
            release_payload("2.3beta", digest=f"sha256:{sha256(installer).hexdigest()}")
        ]).encode()

        def urlopen(request, **_kwargs):
            if "api.github.com" in request.full_url:
                return FakeResponse(payload)
            return FakeResponse(installer, request.full_url)

        service = UpdateService(urlopen=urlopen)
        release = service.check("beta").release
        with tempfile.TemporaryDirectory() as temp:
            result = service.download(release, Path(temp))
            self.assertEqual(result.read_bytes(), installer)

    def test_download_rejects_modified_installer(self):
        payload = json.dumps([
            release_payload("2.3beta", digest="sha256:" + "0" * 64)
        ]).encode()

        def urlopen(request, **_kwargs):
            if "api.github.com" in request.full_url:
                return FakeResponse(payload)
            return FakeResponse(b"test", request.full_url)

        service = UpdateService(urlopen=urlopen)
        release = service.check("beta").release
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(UpdateError, "Prüfsumme"):
                service.download(release, Path(temp))
            self.assertFalse(any(Path(temp).rglob("*.exe")))

    def test_checksum_asset_is_used_when_github_digest_is_missing(self):
        installer = b"test"
        checksum_line = f"{sha256(installer).hexdigest()}  Sorterino_Setup_v2.3beta.exe\n".encode()
        payload = json.dumps([release_payload("2.3beta", checksum=True)]).encode()

        def urlopen(request, **_kwargs):
            if "api.github.com" in request.full_url:
                return FakeResponse(payload)
            if request.full_url.endswith(".sha256"):
                return FakeResponse(checksum_line, request.full_url)
            return FakeResponse(installer, request.full_url)

        service = UpdateService(urlopen=urlopen)
        release = service.check("beta").release
        with tempfile.TemporaryDirectory() as temp:
            result = service.download(release, Path(temp))
            self.assertEqual(result.read_bytes(), installer)

    def test_release_checksum_tool_uses_expected_asset_name(self):
        with tempfile.TemporaryDirectory() as temp:
            installer = Path(temp) / "Sorterino_Setup_v2.2beta.exe"
            installer.write_bytes(b"installer")
            checksum = create_checksum(installer)
            self.assertEqual(checksum.name, f"{installer.name}.sha256")
            self.assertIn(sha256(b"installer").hexdigest(), checksum.read_text(encoding="ascii"))

    def test_installer_launcher_uses_encoded_script_and_child_environment(self):
        if os.name != "nt":
            self.skipTest("Windows launcher")
        with tempfile.TemporaryDirectory() as temp:
            installer = Path(temp) / "Ordner mit Leerzeichen" / "Sorterino_Setup_v2.3beta.exe"
            installer.parent.mkdir()
            installer.write_bytes(b"installer")
            with patch("src.updates.service.subprocess.Popen") as popen:
                launch_installer_after_exit(installer, 1234)
            args = popen.call_args.args[0]
            kwargs = popen.call_args.kwargs
            self.assertIn("-EncodedCommand", args)
            self.assertNotIn(str(installer.resolve()), args)
            self.assertEqual(kwargs["env"]["SORTERINO_UPDATE_PARENT_PID"], "1234")
            self.assertEqual(
                kwargs["env"]["SORTERINO_UPDATE_INSTALLER"], str(installer.resolve())
            )
            self.assertEqual(kwargs["cwd"], str(installer.parent.resolve()))


if __name__ == "__main__":
    unittest.main()
