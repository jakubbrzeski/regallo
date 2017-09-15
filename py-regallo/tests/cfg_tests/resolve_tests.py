import unittest
import utils
import cfg
import cfg.resolve as resolve
import cfg.printer as cfgprinter

class TestOrderMoves(unittest.TestCase):

    # Checks if the actual list of moves is a circular 
    # shift of expected with appended 'Nones'.
    # actual    - computed list of moves .
    # expected  - any correct list of moves (without Nones).
    #
    # Example: 
    # self.assert_cycle(cycle, [(d5, u5), (d4, u4), (d6, u6)]
    # checks whether cycle is equal to ONE of the following:
    # [(None, u5), (d4, u4), (d6, u6), (d5, None)]
    # [(None, u4), (d6, u6), (d5, u5), (d4, None)]
    # [(None, u6), (d5, u5), (d4, u4), (d6, None)]
    def assert_cycle(self, actual, expected):
        for i in range(len(expected)):
            c = expected[i:] + expected[:i]
            shift = [(None, c[0][1])] + c[1:] + [(c[0][0], None)]
            if shift == actual:
                return True

        return False


    def test_complicated(self):
        u1 = resolve.Alloc("u1", "reg1")
        u2 = resolve.Alloc("u2", "reg1")
        u3 = resolve.Alloc("u3", "reg2")
        u4 = resolve.Alloc("u4", "reg4")
        u5 = resolve.Alloc("u5", "reg5")
        u6 = resolve.Alloc("u6", "reg6")
        u7 = resolve.Alloc("u7", None)

        d1 = resolve.Alloc("d1", "reg1")
        d2 = resolve.Alloc("d2", "reg2")
        d3 = resolve.Alloc("d3", "reg3")
        d4 = resolve.Alloc("d4", "reg5")
        d5 = resolve.Alloc("d5", "reg6")
        d6 = resolve.Alloc("d6", "reg4")
        d7 = resolve.Alloc("d7", "reg2")

        moves = [(d1,u1), (d2,u2), (d3,u3), (d4,u4), (d5,u5), (d6,u6), (d7, u7)]
        """
                                         _____
                                        |     |
        (reg3) <------ (reg2) <---- reg(1) <--  (self loop)
                           ^
                            \______ None

        
        + cycle = [reg4, reg5, reg6]

        """

        res, cycles = resolve.order_moves(moves)

        """
        CORRECT ORDER:
         d1   =  u1     (reg1 = reg1) self loop (it may be anywhere actually)

         d3   =  u3     (reg3 = reg2)
         d2   =  u2     (reg2 = reg1)
         d7   =  u7     (reg1 = const)

         None =  u5     (None = reg5)
         d4   =  u4     (reg5 = reg4)
         d6   =  u6     (reg4 = reg6)
         d5   =  None   (reg6 = None)

        """
        self.assertTrue((d1,u1) in res)
        self.assertTrue(res.index((d3, u3)) < res.index((d2, u2)))
        self.assertTrue(res.index((d2, u2)) < res.index((d7, u7)))
        self.assertTrue(len(cycles) == 1)
        self.assert_cycle(cycles[0], [(d5, u5), (d4, u4), (d6, u6)])

    def test_simple(self):
        # 12: v12 = phi bb3 -> v9 bb5 -> v13 
        # 13: v14 = phi bb3 -> v10 bb5 -> v12

        u1 = resolve.Alloc("v13", "reg13")
        u2 = resolve.Alloc("v12", "reg12")
        
        d1 = resolve.Alloc("v12", "reg12")
        d2 = resolve.Alloc("v14", "reg14")
        moves = [(d1, u1), (d2, u2)]
        # reg13 <--- reg12 <--- reg13

        res, cycles = resolve.order_moves(moves)

        self.assertTrue(res.index((d2,u2)) < res.index((d1, u1)))
        self.assertFalse(cycles)

            
class PhiEliminationTests(unittest.TestCase):
   
    def edge(self, bbA, bbB):
        bbB.preds[bbA.id] = bbA
        bbA.succs[bbB.id] = bbB

    def setUp(self):
        f = cfg.Function("f")
        bb0 = cfg.BasicBlock("bb0", f)
        bb1 = cfg.BasicBlock("bb1", f)
        bb2 = cfg.BasicBlock("bb2", f)
        bb3 = cfg.BasicBlock("bb3", f)
        bb4 = cfg.BasicBlock("bb4", f)
        f.bblocks["bb0"] = bb0
        f.bblocks["bb1"] = bb1
        f.bblocks["bb2"] = bb2
        f.bblocks["bb3"] = bb3
        f.bblocks["bb4"] = bb4
        f.entry_bblock = bb4
        self.edge(bb4, bb0)
        self.edge(bb4, bb1)
        self.edge(bb0, bb2)
        self.edge(bb1, bb2)
        self.edge(bb1, bb3)

        """""""""""
             bb4
           /     \ 
          /       \ 
         bb0        bb1
          \       /    \ 
           \     /      \ 
         --- bb2 ---     bb3
        | phi = ... |
        | phi = ... |
        | [...]     |
         -----------

        d1 (reg1) = u1 (reg1)
        d2 (reg2) = u2 (reg1)
        d3 (reg3) = u3 (reg2)

        d4 (reg5) = u4 (reg4)
        d5 (reg6) = u5 (reg5)
        d6 (reg4) = u6 (reg6)

        d7 (reg7) = u7 (None)
        

                                         _____
                                        |     |
        (reg3) <------ (reg2) <---- reg(1) <--  (self loop)
                           ^
                            \______ None

        
        + cycle = [reg4, reg5, reg6]

        """""""""""

        # We add "None" at the beginning for convenience - we wnat to have defs[1] = "v1".
        defs = [None]+[f.get_or_create_variable() for i in range(10)]
        uses = [None]+[f.get_or_create_variable() for i in range(10)]

        # Helper function for creating PHI instruction in bb2 which copy Variables from bb1 and consts from bb0.
        def phi21(d, u, reg_d, reg_u):
            _uses = [("bb1", u)] if isinstance(u, cfg.Variable) else [] 
            i = cfg.Instruction(bb2, d, "phi", uses = _uses, uses_debug = [("bb0", "const"), ("bb1", u)])
            
            if reg_d:
                d.alloc = reg_d
            if reg_u:
                u.alloc = reg_u

            return i

        phi1 = phi21(defs[1], uses[1], "reg1", "reg1")
        phi2 = phi21(defs[2], uses[2], "reg2", "reg1")
        phi3 = phi21(defs[3], uses[3], "reg3", "reg2")

        phi4 = phi21(defs[4], uses[4], "reg5", "reg4")
        phi5 = phi21(defs[5], uses[5], "reg6", "reg5")
        phi6 = phi21(defs[6], uses[6], "reg4", "reg6")

        phi7 = phi21(defs[7], "const", "reg7", None)

        bb2.instructions = [phi1, phi2, phi3, phi4, phi5, phi6, phi7]
        bb2.phis = [phi1, phi2, phi3, phi4, phi5, phi6, phi7]

        self.phis = bb2.phis
        self.f = f
        self.defs = defs
        self.uses = uses

    def assert_mov(self, instr, def_id, use_id, use_const=False, redundant=False):
        self.assertEqual(instr.opname, cfg.Instruction.MOV)
        self.assertIsNotNone(instr.definition)
        self.assertEqual(instr.definition.id, def_id)
        self.assertEqual(instr.is_redundant(), redundant)

        if use_const:
            self.assertFalse(instr.uses)
            self.assertEqual(len(instr.uses_debug), 1)
            use_debug = list(instr.uses_debug)[0]
            self.assertEqual(use_debug, "const")

        else:
            self.assertEqual(len(instr.uses), 1)
            use = list(instr.uses)[0]
            self.assertEqual(use.id, use_id)

    def test_simple(self):
        resolve.eliminate_phi(self.f)


        """
        CORRECT ANSWER
        In a new basic block between bb1 and bb2
        v1   =  v11     (reg1 = reg1) self loop (it may be anywhere actually)

        v3   =  v13     (reg3 = reg2)
        v2   =  v12     (reg2 = reg1)
        v7   =  const     (reg1 = const)

        None =  v15     (None = reg5)
        v4   =  v14     (reg5 = reg4)
        v6   =  v16     (reg4 = reg6)
        v5   =  None    (reg6 = None)


        """


        new_bb = None
        for bb in self.f.bblocks.values():
            if len(bb.preds) == 1 and len(bb.succs) == 1 and "bb1" in bb.preds and "bb2" in bb.succs:
                new_bb = bb


        # Assert new block between bb1 nad bb2 has been created.
        self.assertIsNotNone(new_bb)
        self.assertEquals(len(new_bb.instructions), 8)
        self.assert_mov(new_bb.instructions[0], "v1", "v11", redundant=True)
        self.assert_mov(new_bb.instructions[1], "v3", "v13")
        self.assert_mov(new_bb.instructions[2], "v2", "v12")
        # TODO: finish , add mem-mem move


