import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import ezdxf


PROJECT = Path(__file__).resolve().parent
TEST_PROJECT = PROJECT / "CadTextCreator.Tests" / "CadTextCreator.Tests.csproj"
LIBRARY = PROJECT / "font-library.json"


@unittest.skipUnless(shutil.which("dotnet"), ".NET SDK is not installed")
class CSharpPipelineTests(unittest.TestCase):
    def test_composes_and_exports_closed_dxf_contours(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.dxf"
            environment = os.environ.copy()
            environment["DOTNET_ROLL_FORWARD"] = "Major"
            subprocess.run(
                [
                    "dotnet",
                    "run",
                    "--project",
                    str(TEST_PROJECT),
                    "--",
                    str(LIBRARY),
                    "dejavu-sans-book",
                    str(output),
                ],
                cwd=PROJECT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )

            document = ezdxf.readfile(output)
            entities = list(document.modelspace().query("LWPOLYLINE"))
            self.assertEqual(10, len(entities))
            self.assertTrue(all(entity.closed for entity in entities))
            self.assertEqual({"TEXT_OUTLINES"}, {entity.dxf.layer for entity in entities})
            self.assertEqual("AC1021", document.dxfversion)

            vertices = [
                point[:2]
                for entity in entities
                for point in entity.get_points()
            ]
            bounds = (
                min(point[0] for point in vertices),
                min(point[1] for point in vertices),
                max(point[0] for point in vertices),
                max(point[1] for point in vertices),
            )
            expected = (98.596407, -49.364958, 182.659763, -15.565815)
            for actual, target in zip(bounds, expected):
                self.assertAlmostEqual(target, actual, places=5)


if __name__ == "__main__":
    unittest.main()
