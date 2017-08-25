import unittest

class CFGTests(unittest.TestCase):

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

