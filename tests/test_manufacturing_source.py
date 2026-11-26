"""Verify the versioned native manufacturing inputs and delivered BREP exports."""
import hashlib
import json
import unittest
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import cadquery as cq
import yaml

ROOT = Path(__file__).resolve().parent.parent


class ManufacturingSourceTests(unittest.TestCase):
    def test_manifest_plate_membership_and_current_native_exports(self):
        manifest = yaml.safe_load((ROOT / 'manufacturing.yaml').read_text())
        report = json.loads((ROOT / 'docs/validation.json').read_text())['native_manufacturing']
        source = ROOT / manifest['spec']['source']['document']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), report['source_sha256'])
        self.assertFalse(manifest['spec']['deployment']['autoPrint'])
        with ZipFile(ROOT / manifest['spec']['slicer']['project']) as archive:
            settings = ET.fromstring(archive.read('Metadata/model_settings.config'))
            for plate in manifest['spec']['plates']:
                matches = [p for p in settings.findall('plate') if any(
                    m.get('key') == 'plater_name' and m.get('value') == plate['name']
                    for m in p.findall('metadata'))]
                self.assertEqual(len(matches), 1)
                actual = {m.get('value') for m in matches[0].findall('model_instance/metadata')
                          if m.get('key') == 'object_id'}
                self.assertEqual(actual, {o['projectObjectId'] for o in plate['objects']})
                for obj in plate['objects']:
                    self.assertIn(obj['meshPath'], archive.namelist())
                    step = ROOT / 'cad/freecad' / Path(obj['export']).with_suffix('.step')
                    solid = cq.importers.importStep(str(step)).val()
                    self.assertTrue(solid.isValid(), obj['id'])
                    self.assertEqual(len(solid.Solids()), 1)
                    self.assertAlmostEqual(solid.Volume(), report['geometry'][obj['id']]['volume'],
                                           delta=0.02)
        for name, checksum in report['exports'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), checksum)
        for name in ('LeftBracketTrussV2', 'RightBracketTrussV2'):
            comparison = report['diameter_comparison'][name]
            self.assertEqual(comparison['bearing_region_symmetric_difference_mm3'], 0)
            self.assertEqual(comparison['added_volume'], 0)
            self.assertGreater(comparison['removed_volume'], 0)


if __name__ == '__main__':
    unittest.main()
