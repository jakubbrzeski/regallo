import unittest
import cfg
import lscan
import cfgmocks

"""
FUNCTION gcd
bb1 (entry)
   0: v1 = icmp v2 v3
   1: v4 = br v1 bb3 bb2

bb2 (if.then)
   2: v5 = xor v2 v3
   3: v6 = xor v3 v5
   4: v7 = xor v5 v6
   5: v8 = br bb3

bb3 (if.end)
   6: v9 = phi (bb2 -> v6) (bb1 -> v3)
   7: v10 = phi (bb2 -> v7) (bb1 -> v2)
   8: v11 = br bb4

bb4 (while.cond)
   9: v12 = phi (bb3 -> v9) (bb5 -> v13)
   10: v14 = phi (bb3 -> v10) (bb5 -> v12)
   11: v15 = icmp v12 const
   12: v16 = br v15 bb6 bb5

bb5 (while.body)
   13: v13 = srem v14 v12
   14: v17 = br bb4

bb6 (while.end)
   15: v18 = ret v14
"""

class BasicLinearScanTest(cfgmocks.GCDTest):

    def setUp(self):
        super(BasicLinearScanTest, self).setUp()
        self.bls = lscan.BasicLinearScan(self.f)
        print "BasicLinearScanTest setup"

    def test_intervals(self):
        intervals = self.bls.compute_intervals()

        def assertInterval(vid, num_fr, num_to, num_def, num_uses):
            self.assertIn(vid, intervals)
            # In basic linear scan each variable should have only one interval 
            # with only one subinterval.
            self.assertEqual(len(intervals[vid]), 1)
            iv = intervals[vid][0]
            self.assertEqual(iv.fr.num, num_fr)
            self.assertEqual(iv.to.num, num_to)
            # Def
            if num_def is not None:
                self.assertIsNotNone(iv.defn)
                self.assertEqual(iv.defn.num, num_def)
            else:
                self.assertIsNone(iv.defn)
            # Uses
            self.assertEqual(len(iv.uses), len(num_uses))
            iv_num_uses = sorted([use.num for use in iv.uses])
            num_uses = sorted(num_uses)
            for i in range(len(num_uses)):
                self.assertEqual(iv_num_uses[i], num_uses[i])
                
        def assertEmptyInterval(vid):
            self.assertEqual(len(intervals[vid]), 1)
            self.assertTrue(intervals[vid][0].empty())

        assertInterval("v1", 0, 1, 0, [1])
        assertInterval("v2", 0, 7, None, [0, 2, 7])
        assertInterval("v3", 0, 6, None, [0, 2, 3, 6])
        assertEmptyInterval("v4")
        assertInterval("v5", 2, 4, 2, [3,4])
        assertInterval("v6", 3, 6, 3, [4, 6])
        assertInterval("v7", 4, 7, 4, [7])
        assertEmptyInterval("v8")
        assertInterval("v9", 6, 14, 6, [9])
        assertInterval("v10", 7, 14, 7, [10])
        assertEmptyInterval("v11")
        assertInterval("v12", 9, 13, 9, [10, 11, 13])
        assertInterval("v13", 9, 14, 13, [9])
        assertInterval("v14", 10, 15, 10, [13, 15])
        assertInterval("v15", 11, 12, 11, [12])
        assertEmptyInterval("v16")
        assertEmptyInterval("v17")
        assertEmptyInterval("v18")








