import unittest
import cfg
import cfg.analysis as analysis

class GCDTest(unittest.TestCase):
    """
    TestCase based on the following function
    computing greatest common divisor.

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

    def setUp(self):
        f = cfg.Function("gcd")
        
        var = {}
        for i in range(1,19):
            vid = "v"+str(i)
            var[vid] = f.get_or_create_variable(str(vid))

        # Basic blocks and instructions:
        bb1 = cfg.BasicBlock("bb1", f, "entry")
        i0 = cfg.Instruction(bb1, var["v1"], "icmp", [var["v2"], var["v3"]], 
                uses_debug=["v2","v3"])
        i1 = cfg.Instruction(bb1, var["v4"], "br", [var["v1"]], 
                uses_debug=["v1", "bb3", "bb2"])
        bb1.set_instructions([i0,i1])

        bb2 = cfg.BasicBlock("bb2", f, "if.then")
        i2 = cfg.Instruction(bb2, var["v5"], "xor", [var["v2"], var["v3"]], 
                uses_debug=["v2", "v3"])
        i3 = cfg.Instruction(bb2, var["v6"], "xor", [var["v3"], var["v5"]], 
                uses_debug=["v3", "v5"])
        i4 = cfg.Instruction(bb2, var["v7"], "xor", [var["v5"], var["v6"]], 
                uses_debug=["v5", "v6"])
        i5 = cfg.Instruction(bb2, var["v8"], "br", [], uses_debug=["bb4"])
        bb2.set_instructions([i2, i3, i4, i5])

        bb3 = cfg.BasicBlock("bb3", f, "if.end")
        i6 = cfg.Instruction(bb3, var["v9"], "phi", [("bb2", var["v6"]), ("bb1", var["v3"])],
                uses_debug=[("bb2", var["v6"]), ("bb1", var["v3"])])
        i7 = cfg.Instruction(bb3, var["v10"], "phi", [("bb2", var["v7"]), ("bb1",var["v2"])],
                uses_debug=[("bb2", var["v7"]), ("bb1",var["v2"])])
        i8 = cfg.Instruction(bb3, var["v11"], "br", [], uses_debug=["bb4"])
        bb3.set_instructions([i6, i7, i8])

        bb4 = cfg.BasicBlock("bb4", f, "while.cond")
        i9 = cfg.Instruction(bb4, var["v12"], "phi", [("bb3", var["v9"]), ("bb5", var["v13"])],
                uses_debug=[("bb3", var["v9"]), ("bb5", var["v13"])])
        i10 = cfg.Instruction(bb4, var["v14"], "phi", [("bb3", var["v10"]), ("bb5", var["v12"])],
                uses_debug=[("bb3", var["v10"]), ("bb5", var["v12"])])
        i11 = cfg.Instruction(bb4, var["v15"], "icmp", [var["v12"]], 
                uses_debug=["v12", "const"])
        i12 = cfg.Instruction(bb4, var["v16"], "br", [var["v15"]], 
                uses_debug=["v15", "bb6", "bb5"])
        bb4.set_instructions([i9, i10, i11, i12])

        bb5 = cfg.BasicBlock("bb5", f, "while.body")
        i13 = cfg.Instruction(bb5, var["v13"], "srem", [var["v14"], var["v12"]], 
                uses_debug=["v14", "v12"])
        i14 = cfg.Instruction(bb5, var["v17"], "br", [], uses_debug=["bb4"])
        bb5.set_instructions([i13, i14])

        bb6 = cfg.BasicBlock("bb6", f, "while.end")
        i15 = cfg.Instruction(bb6, var["v18"], "ret", [var["v14"]], uses_debug=["v14"])
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

        analysis.perform_full_analysis(f)
        self.f = f


