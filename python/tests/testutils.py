import unittest

class CFGTestCase(unittest.TestCase):

    def assert_instruction(self, instr, **kwargs):
        iid = kwargs.get("iid", None)
        opname = kwargs.get("opname", None)
        defn = kwargs.get("defn", None)
        uses = kwargs.get("uses", None)
        uses_debug = kwargs.get("uses_debug", None)

        if iid is not None:
            self.assertEqual(instr.id, iid)

        if opname is not None:
            self.assertEqual(instr.opname, opname)

        self.assertEqual(instr.definition, defn)

        if uses is not None:
            self.assertEqual(instr.uses, uses)

        if uses_debug is not None:
            self.assertEqual(instr.uses_debug, uses_debug)

    def assert_edge(self, bb1, bb2):
        self.assertIn(bb1.id, bb2.preds)
        self.assertIn(bb2.id, bb1.succs)

    def assert_no_edge(self, bb1, bb2):
        self.assertNotIn(bb1.id, bb2.preds)
        self.assertNotIn(bb2.id, bb1.succs)

    def assert_interval(self, iv, fr_num, to_num, def_num, uses_nums, subintervals_nums=None):
        self.assertEqual(iv.fr.num, fr_num)
        self.assertEqual(iv.to.num, to_num)

        # Def
        if def_num is not None:
            self.assertIsNotNone(iv.defn)
            self.assertEqual(iv.defn.num, def_num)
        else:
            self.assertIsNone(iv.defn)

        # Uses
        self.assertEqual(len(iv.uses), len(uses_nums))
        iv_uses_nums = sorted([use.num for use in iv.uses])
        uses_nums = sorted(uses_nums)
        for n1, n2 in zip(iv_uses_nums, uses_nums):
            self.assertEqual(n1, n2)

        # Subintervals
        if subintervals_nums:
            self.assertIsNotNone(iv.subintervals)
            self.assertEqual(len(iv.subintervals), len(subintervals_nums))
            iv_sub_nums = sorted([(sub.fr.num, sub.to.num) for sub in iv.subintervals])
            sub_nums = sorted(subintervals_nums)
            for p1, p2 in zip(iv_sub_nums, sub_nums):
                self.assertEqual(p1[0], p2[0])
                self.assertEqual(p1[1], p2[1])


