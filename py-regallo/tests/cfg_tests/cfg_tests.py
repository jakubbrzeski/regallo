import unittest
import cfg
import tests.cfgmocks as cfgmocks
from copy import deepcopy


class CopyTests(cfgmocks.GCDTest):

    def test_copy_var(self):
        for vid, var in self.f.vars.iteritems():
            c = deepcopy(var)
            self.assertEqual(c.id, var.id)
            self.assertEqual(c.alloc, var.alloc)
            self.assertEqual(c.llvm_name, var.llvm_name)

class LivenessWithAllocTests(unittest.TestCase):

    def assert_module(self, m):
        m.perform_full_analysis()
        for f in m.functions.values():
            result = f.perform_liveness_analysis()
            self.assertTrue(result)
            for bb in f.bblocks.values():
                self.assertEqual(bb.live_in, set(bb.live_in_with_alloc.keys()))
                self.assertEqual(bb.live_out, set(bb.live_out_with_alloc.keys()))

    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        self.assert_module(m)

    def test_sort(self):
        m = cfg.Module.from_file("programs/sort.json")
        self.assert_module(m)

    def test_sort(self):
        m = cfg.Module.from_file("programs/gjk.json")
        self.assert_module(m)
