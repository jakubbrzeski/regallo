import unittest
import cfgmocks
from copy import deepcopy


class CopyTests(cfgmocks.GCDTest):

    def test_copy_var(self):
        for vid, var in self.f.vars.iteritems():
            c = deepcopy(var)
            self.assertEqual(c.id, var.id)
            self.assertEqual(c.alloc, var.alloc)
            self.assertEqual(c.llvm_name, var.llvm_name)

    def test_copy_instr(self):
        pass

