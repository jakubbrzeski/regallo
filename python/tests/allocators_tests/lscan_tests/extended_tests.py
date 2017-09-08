import unittest
from tests.cfgmocks import GCDTest
from allocators.lscan.intervals import ExtendedInterval
from allocators.lscan.advanced import ExtendedLinearScan

class ExtendedLinearScanTest(GCDTest):

    def test_compute_intervals(self):
        als = ExtendedLinearScan(self.f) 
        intervals = als.compute_intervals()
        self.assertIn("v14", intervals)
        self.assertEqual(len(intervals["v14"]), 1)
        self.assert_interval(intervals["v14"][0], 10, 15, 10, [13, 15], [(10, 13), (15, 15)])

"""
[9, 14]    v12         -   [9, 14]
[10, 15]   v14         -   [10, 13] [15, 15]
[11, 12]   v15         -   [11, 12]
[13, 14]   v13         -   [13, 14]
"""
