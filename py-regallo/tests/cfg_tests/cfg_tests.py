import unittest
import cfg
import tests.cfgmocks as cfgmocks
from copy import deepcopy, copy


class CopyTests(cfgmocks.GCDTest):

    def test_copy_var(self):
        v = cfg.Variable("v0")
        v.alloc = "reg1"
       
        s = set([v])
        w = list(s)[0]
        self.assertEqual(v.alloc, w.alloc)
