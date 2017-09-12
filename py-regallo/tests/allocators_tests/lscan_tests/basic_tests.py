import unittest
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.basic import spillers
import tests.cfgmocks as cfgmocks
import cfg


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
        [6, 8.5]   v9            -     
        [7, 8.5]   v10           -     
        [9, 14.5]  v12           -     
        [10, 15]   v14           -     
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
        assertInterval("v9", 6, 8.5, 6, [9])
        assertInterval("v10", 7, 8.5, 7, [10])
        self.assertNotIn("v11", intervals)
        assertInterval("v12", 9, 14.5, 9, [10, 11, 13])
        assertInterval("v13", 13, 14.5, 13, [9])
        assertInterval("v14", 10, 15, 10, [13, 15])
        assertInterval("v15", 11, 12, 11, [12])
        self.assertNotIn("v16", intervals)
        self.assertNotIn("v17", intervals)
        self.assertNotIn("v18", intervals)

# Performs sanity check after each allocation.
# If allocation succeeded, sanity check also must succeed.
class AllocationCorrectnessTests(unittest.TestCase):

    def setUp(self):
        self.allocators = [
                BasicLinearScan(),
                BasicLinearScan(spiller=spillers.CurrentFirst(), name="current"),
                BasicLinearScan(spiller=spillers.LessUsedFirst(), name="lessUsed")]


    def assert_allocation_correct(self, m, allocator, regcount):
        for f in m.functions.values():
            g = f.copy()
            success = allocator.perform_full_register_allocation(g, regcount)
            if success:

                correct = g.allocation_is_correct()
                if not correct:
                    print "Function: ", g.name, " allocator:", allocator.name, "rc:", regcount 
                self.assertTrue(correct)
    
    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        m.perform_full_analysis()
        for allocator in self.allocators:
            self.assert_allocation_correct(m, allocator, 2)
            self.assert_allocation_correct(m, allocator, 3)
            self.assert_allocation_correct(m, allocator, 4)
            self.assert_allocation_correct(m, allocator, 5)
       
    def test_sort(self):
        m = cfg.Module.from_file("programs/gcd.json")
        m.perform_full_analysis()
        for allocator in self.allocators:
            self.assert_allocation_correct(m, allocator, 2)
            self.assert_allocation_correct(m, allocator, 3)
            self.assert_allocation_correct(m, allocator, 4)
            self.assert_allocation_correct(m, allocator, 5)

    def test_gjk(self):
        m = cfg.Module.from_file("programs/gjk.json")
        m.perform_full_analysis()
        for allocator in self.allocators:
            self.assert_allocation_correct(m, allocator, 3)
            self.assert_allocation_correct(m, allocator, 5)
            self.assert_allocation_correct(m, allocator, 7)
            self.assert_allocation_correct(m, allocator, 8)

    def test_fft(self):
        m = cfg.Module.from_file("programs/fft.json")
        m.perform_full_analysis()
        for allocator in self.allocators:
            self.assert_allocation_correct(m, allocator, 3)
            self.assert_allocation_correct(m, allocator, 5)
            self.assert_allocation_correct(m, allocator, 7)
            self.assert_allocation_correct(m, allocator, 8)
