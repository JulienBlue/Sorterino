import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TEMPLATE = PROJECT_ROOT / "store" / "AppxManifest.xml.in"


class StorePackageTests(unittest.TestCase):
    def test_manifest_has_partner_center_identity(self):
        root = ET.fromstring(
            MANIFEST_TEMPLATE.read_text(encoding="utf-8").replace(
                "@PACKAGE_VERSION@", "2.2.5.0"
            )
        )
        namespace = {"f": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
        identity = root.find("f:Identity", namespace)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.attrib["Name"], "JulienBlueHirte.Sorterino")
        self.assertEqual(
            identity.attrib["Publisher"],
            "CN=ADB34DB7-2F09-45A8-9D01-F77F334B36D9",
        )
        self.assertEqual(identity.attrib["ProcessorArchitecture"], "x64")

    def test_manifest_launches_the_packaged_executable(self):
        root = ET.fromstring(
            MANIFEST_TEMPLATE.read_text(encoding="utf-8").replace(
                "@PACKAGE_VERSION@", "2.2.5.0"
            )
        )
        namespace = {"f": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
        application = root.find("f:Applications/f:Application", namespace)
        self.assertIsNotNone(application)
        self.assertEqual(application.attrib["Executable"], "Sorterino\\Sorterino.exe")
        self.assertEqual(application.attrib["EntryPoint"], "Windows.FullTrustApplication")


if __name__ == "__main__":
    unittest.main()
