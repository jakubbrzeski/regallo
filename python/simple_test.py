import unittest
import cfg
import cfg_pretty_printer as cfgprinter
"""
Intervals:
[-1, 6] v3
[-1, 7] v2
[0, 1] v1
[2, 4] v5
[3, 6] v6
[4, 7] v7
[6, 14] v9
[7, 14] v10
[9, 13] v12
[9, 14] v13
[10, 15] v14
[11, 12] v15
"""

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
class SimpleGCDTest(unittest.TestCase):
    def setUp(self):
        # Create gcd funtion based on llvm output.
        f = cfg.Function("gcd")
        
        # Variables:
        var = {}
        for i in range(1,19):
            vid = "v"+str(i)
            var[vid] = f.get_or_create_variable(str(vid))

        # Basic blocks and instructions:
        bb1 = cfg.BasicBlock("bb1", f, "entry")
        i0 = cfg.Instruction(f.get_free_iid(), bb1, var["v1"], "icmp", [var["v2"], var["v3"]], 
                uses_debug=["v2","v3"])
        i1 = cfg.Instruction(f.get_free_iid(), bb1, var["v4"], "br", [var["v1"]], 
                uses_debug=["v1", "bb3", "bb2"])
        bb1.set_instructions([i0,i1])

        bb2 = cfg.BasicBlock("bb2", f, "if.then")
        i2 = cfg.Instruction(f.get_free_iid(), bb2, var["v5"], "xor", [var["v2"], var["v3"]], 
                uses_debug=["v2", "v3"])
        i3 = cfg.Instruction(f.get_free_iid(), bb2, var["v6"], "xor", [var["v3"], var["v5"]], 
                uses_debug=["v3", "v5"])
        i4 = cfg.Instruction(f.get_free_iid(), bb2, var["v7"], "xor", [var["v5"], var["v6"]], 
                uses_debug=["v5", "v6"])
        i5 = cfg.Instruction(f.get_free_iid(), bb2, var["v8"], "br", [], uses_debug=["bb4"])
        bb2.set_instructions([i2, i3, i4, i5])

        bb3 = cfg.BasicBlock("bb3", f, "if.end")
        i6 = cfg.Instruction(f.get_free_iid(), bb3, var["v9"], "phi", [var["v6"], var["v3"]],
                phi_preds=["bb2", "bb1"], uses_debug=[var["v6"], var["v3"]])
        i7 = cfg.Instruction(f.get_free_iid(), bb3, var["v10"], "phi", [var["v7"], var["v2"]],
                phi_preds=["bb2", "bb1"], uses_debug=[var["v7"], var["v2"]])
        i8 = cfg.Instruction(f.get_free_iid(), bb3, var["v11"], "br", [], uses_debug=["bb4"])
        bb3.set_instructions([i6, i7, i8])

        bb4 = cfg.BasicBlock("bb4", f, "while.cond")
        i9 = cfg.Instruction(f.get_free_iid(), bb4, var["v12"], "phi", [var["v9"], var["v13"]],
                phi_preds=["bb3", "bb5"], uses_debug=[var["v9"], var["v13"]])
        i10 = cfg.Instruction(f.get_free_iid(), bb4, var["v14"], "phi", [var["v10"], var["v12"]],
                phi_preds=["bb3", "bb5"], uses_debug=[var["v10"], var["v12"]])
        i11 = cfg.Instruction(f.get_free_iid(), bb4, var["v15"], "icmp", [var["v12"]], 
                uses_debug=["v12", "const"])
        i12 = cfg.Instruction(f.get_free_iid(), bb4, var["v16"], "br", [var["v15"]], 
                uses_debug=["v15", "bb6", "bb5"])
        bb4.set_instructions([i9, i10, i11, i12])

        bb5 = cfg.BasicBlock("bb5", f, "while.body")
        i13 = cfg.Instruction(f.get_free_iid(), bb5, var["v13"], "srem", [var["v14"], var["v12"]], 
                uses_debug=["v14", "v12"])
        i14 = cfg.Instruction(f.get_free_iid(), bb5, var["v14"], "br", [], uses_debug=["bb4"])
        bb5.set_instructions([i13, i14])

        bb6 = cfg.BasicBlock("bb6", f, "while.end")
        i15 = cfg.Instruction(f.get_free_iid(), bb6, var["v18"], "ret", [var["v14"]], uses_debug=["v14"])
        bb6.set_instructions([i15])

        # set up predecessors and successors
        bb2.preds["bb1"] = bb1
        bb3.preds["bb1"] = bb1
        bb3.preds["bb2"] = bb2
        bb4.preds["bb3"] = bb3
        bb4.preds["bb5"] = bb5
        bb5.preds["bb4"] = bb4
        bb6.preds["bb4"] = bb4

        bb1.succs["bb2"] = bb2
        bb1.succs["bb3"] = bb3
        bb2.succs["bb3"] = bb3
        bb3.succs["bb4"] = bb4
        bb5.succs["bb4"] = bb4
        bb4.succs["bb5"] = bb5
        bb4.succs["bb6"] = bb6

        # dictionary
        d = {}
        d["bb1"] = bb1
        d["bb2"] = bb2
        d["bb3"] = bb3
        d["bb4"] = bb4
        d["bb5"] = bb5
        d["bb6"] = bb6

        f.set_bblocks(d, bb1)
        self.f = f

    def test_anything(self):
        print cfgprinter.function_str(self.f)
        self.assertEqual(self.f.name, "gcd")

