import unittest
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.basic import spillers
import tests.cfgmocks as cfgmocks
import cfg
import cfg.sanity
import cfg.analysis as analysis


class BasicLinearScanTest(cfgmocks.GCDTest):

    def setUp(self):
        super(BasicLinearScanTest, self).setUp()
        self.bls = BasicLinearScan()

    def test_compute_intervals(self):
        intervals = self.bls.compute_intervals(self.f)

        def assertInterval(vid, fr, to, def_num, uses_nums):
            self.assertIn(vid, intervals)
            self.assertEqual(len(intervals[vid]), 1)
            iv = intervals[vid][0]

            # Endpoints
            self.assertEqual(iv.fr, fr)
            self.assertEqual(iv.to, to)

            # Def
            if def_num is not None:
                self.assertIsNotNone(iv.defn)
                self.assertEqual(iv.defn.num, def_num)
            else:
                self.assertIsNone(iv.defn)

            # Uses
            self.assertEqual(len(iv.uses), len(uses_nums))
            actual= sorted([use.num for use in iv.uses])
            expected = sorted(uses_nums)
            self.assertEqual(actual, expected)

        """
        Correct answer:
        INTERVAL   VAR-ID       REG    
        [-0.5, 2]  v2            -     
        [-0.5, 3]  v3            -     
        [0, 1]     v1            -     
        [2, 4]     v5            -     
        [3, 5.5]   v6            -     
        [4, 5.5]   v7            -     
        [5.5, 8.5]   v9            -     
        [5.5, 8.5]   v10           -     
        [8.5, 14.5]  v12           -     
        [8.5, 15]   v14           -     
        [11, 12]   v15           -     
        [13, 14.5] v13           - 

        """

        assertInterval("v1", 0, 1, 0, [1])
        assertInterval("v2", -0.5, 2, None, [0, 2, 7])
        assertInterval("v3", -0.5, 3, None, [0, 2, 3, 6])
        self.assertNotIn("v4", intervals)
        assertInterval("v5", 2, 4, 2, [3,4])
        assertInterval("v6", 3, 5.5, 3, [4, 6])
        assertInterval("v7", 4, 5.5, 4, [7])
        self.assertNotIn("v8", intervals)
        assertInterval("v9", 5.5, 8.5, 6, [9])
        assertInterval("v10", 5.5, 8.5, 7, [10])
        self.assertNotIn("v11", intervals)
        assertInterval("v12", 8.5, 14.5, 9, [10, 11, 13])
        assertInterval("v13", 13, 14.5, 13, [9])
        assertInterval("v14", 8.5, 15, 10, [13, 15])
        assertInterval("v15", 11, 12, 11, [12])
        self.assertNotIn("v16", intervals)
        self.assertNotIn("v17", intervals)
        self.assertNotIn("v18", intervals)

