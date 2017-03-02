from frapalyzer import FRAPalyzer
from os import path
import unittest


class TestFrapalyzer(unittest.TestCase):
    def setUp(self):
        dir_path = path.dirname(path.realpath(__file__))
        self.files = [
            path.join(dir_path, 'test_data/data001.nd2'),
            path.join(dir_path, 'test_data/data002.nd2')
        ]

    def test_get_background_roi_001(self):
        with FRAPalyzer(self.files[0]) as analyzer:
            self.assertIsNotNone(analyzer.background_roi)

    def test_get_stim_roi_001(self):
        with FRAPalyzer(self.files[0]) as analyzer:
            self.assertIsNotNone(analyzer.stimulation_roi)

    def test_get_ref_roi_001(self):
        with FRAPalyzer(self.files[0]) as analyzer:
            self.assertIsNotNone(analyzer.reference_roi)

    def test_get_mean_stim_001(self):
        with FRAPalyzer(self.files[0]) as analyzer:
            mean = analyzer.get_mean_intensity(analyzer.stimulation_roi, False, True, True)
            self.assertAlmostEqual(mean, 112, places=0)