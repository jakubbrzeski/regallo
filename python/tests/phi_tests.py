import unittest
from testutils import CFGTests
import utils
import cfg
import phi
from phi import Alloc
import cfgprinter as cfgpr


class TestOrderMoves(CFGTests):

    def assert_cycle(self, moves, result):
        for i in range(len(moves)):
            c = moves[i:] + moves[:i]
            tmp = [(None, c[0][1])] + c[1:] + [(c[0][0], None)]
            print tmp 
            if tmp == result:
                return True

        return False


    def test_complicated(self):
        u1 = Alloc("u1", "reg1")
        u2 = Alloc("u2", "reg1")
        u3 = Alloc("u3", "reg2")
        u4 = Alloc("u4", "reg4")
        u5 = Alloc("u5", "reg5")
        u6 = Alloc("u6", "reg6")

        d1 = Alloc("d1", "reg1")
        d2 = Alloc("d2", "reg2")
        d3 = Alloc("d3", "reg3")
        d4 = Alloc("d4", "reg5")
        d5 = Alloc("d5", "reg6")
        d6 = Alloc("d6", "reg4")

        loclist = [(d1,u1), (d2,u2), (d3,u3), (d4,u4), (d5,u5), (d6,u6)]
        res = phi.order_moves(loclist)

        """
        ( d3  =  u3 )
        ( d2  =  u2 )
        ( None  =  u5 )
        ( d4  =  u4 )
        ( d6  =  u6 )
        ( d5  =  None )
        """

        self.assertTrue(res.index((d3, u3)) < res.index((d2, u2)))

    def test_simple(self):
        # 12: v12 = phi bb3 -> v9 bb5 -> v13 
        # 13: v14 = phi bb3 -> v10 bb5 -> v12

        u1 = Alloc("v13", "reg13")
        u2 = Alloc("v12", "reg12")
        
        d1 = Alloc("v12", "reg12")
        d2 = Alloc("v14", "reg14")
        moves = [(d1, u1), (d2, u2)]
        res = phi.order_moves(moves)

        self.assertTrue(res.index((d2,u2)) < res.index((d1, u1)))

    def test_cycle(self):
        # v1 = ... v2
        # v2 = ... v3
        # v3 = ... v1
        u1 = Alloc("v1", "reg1")
        u2 = Alloc("v2", "reg2")
        u3 = Alloc("v3", "reg3")

        d1 = Alloc("v1", "reg1")
        d2 = Alloc("v2", "reg2")
        d3 = Alloc("v3", "reg3")

        m1 = (d1, u2)
        m2 = (d2, u3)
        m3 = (d3, u1)
        moves = [m1, m2, m3]
        res = phi.order_moves(moves)

        self.assertTrue(self.assert_cycle(moves, res))
        

class PhiEliminationTests(CFGTests):
   
    def edge(self, bbA, bbB):
        bbB.preds[bbA.id] = bbA
        bbA.succs[bbB.id] = bbB

    def setUp(self):
        f = cfg.Function("f")
        bb0 = cfg.BasicBlock("bb0", f)
        bb1 = cfg.BasicBlock("bb1", f)
        bb2 = cfg.BasicBlock("bb2", f)
        f.bblocks["bb1"] = bb1
        f.bblocks["bb2"] = bb2
        self.edge(bb0, bb2)
        self.edge(bb1, bb2)

        # bb2:
        # v12 = phi (...) ; bb1 -> v13 
        # v14 = phi (...) ; bb1 -> v12
        v12 = f.get_or_create_variable("v12") 
        v13 = f.get_or_create_variable("v13")
        v14 = f.get_or_create_variable("v14")

        phi1 = cfg.Instruction(bb2, v12, "phi", [("bb1", v13)], [("bb0", "const"), ("bb1", v13)])
        phi2 = cfg.Instruction(bb2, v14, "phi", [("bb1", v12)], [("bb0", "const"), ("bb1", v12)])
        bb2.instructions = [phi1, phi2]
        bb2.phis = [phi1, phi2]

        self.f = f
        self.bb0 = bb0
        self.bb1 = bb1
        self.bb2 = bb2
        self.phi1 = phi1
        self.phi2 = phi2
        self.v12 = v12
        self.v13 = v13
        self.v14 = v14

    def test_const(self):
        self.v12.alloc[self.phi1.id] = "reg12"
        self.v13.alloc[self.phi1.id] = "reg13"
        
        self.v14.alloc[self.phi2.id] = utils.slot(self.v14)
        self.v12.alloc[self.phi2.id] = "reg12"
        phi.eliminate_phi_in_bb(self.bb2)

        self.assertEqual(len(self.bb0.instructions), 2)
        i0 = self.bb0.instructions[0]
        i1 = self.bb0.instructions[1]
        
        self.assertTrue(i0.opname==cfg.Instruction.MOV or i1.opname==cfg.Instruction.MOV)
        if i1.opname==cfg.Instruction.MOV:
            tmp = i0
            i0 = i1
            i1 = tmp

        self.assert_instruction(i0, opname=cfg.Instruction.MOV, defn=self.v12, 
                uses_debug=["const"])
        self.assert_instruction(i1, opname=cfg.Instruction.STORE, defn=None, 
                uses_debug=[utils.slot(self.v14), "const"])
        

    def test_reg_reg(self):
        # Different allocation cases:
        # REG - REG
        self.v12.alloc[self.phi1.id] = "reg12"
        self.v13.alloc[self.phi1.id] = "reg13"
        
        self.v14.alloc[self.phi2.id] = "reg14"
        self.v12.alloc[self.phi2.id] = "reg12"
        phi.eliminate_phi_in_bb(self.bb2)

        self.assertEqual(len(self.bb1.instructions), 2)
        i0 = self.bb1.instructions[0]
        i1 = self.bb1.instructions[1]
        
        self.assert_instruction(i0, opname=cfg.Instruction.MOV, defn=self.v14, uses=[self.v12])
        self.assert_instruction(i1, opname=cfg.Instruction.MOV, defn=self.v12, uses=[self.v13])

    def test_mem_mem(self):
        # MEM - MEM
        self.v12.alloc[self.phi1.id] = utils.slot(self.v12)
        self.v13.alloc[self.phi1.id] = utils.slot(self.v13)
        
        self.v14.alloc[self.phi2.id] = utils.slot(self.v14)
        self.v12.alloc[self.phi2.id] = utils.slot(self.v12)
        phi.eliminate_phi_in_bb(self.bb2)

        self.assertEqual(len(self.bb1.instructions), 4)
        i0 = self.bb1.instructions[0]
        i1 = self.bb1.instructions[1]
        i2 = self.bb1.instructions[2]
        i3 = self.bb1.instructions[3]

        v0  = self.f.temp_variable()
        self.assert_instruction(i0, opname=cfg.Instruction.LOAD, defn=v0, uses=[],
                uses_debug=[utils.slot(self.v12)])
        self.assert_instruction(i1, opname=cfg.Instruction.STORE, defn=None, uses=[v0])
        self.assert_instruction(i2, opname=cfg.Instruction.LOAD, defn=v0, uses=[],
                uses_debug=[utils.slot(self.v13)])
        self.assert_instruction(i3, opname=cfg.Instruction.STORE, defn=None, uses=[v0])

    def test_inserting_bb(self):
        bb3 = cfg.BasicBlock("bb3", self.f)
        self.f.bblocks["bb3"] = bb3
        self.edge(self.bb1, bb3)
       
        # the same as in test_reg_reg
        self.v12.alloc[self.phi1.id] = "reg12"
        self.v13.alloc[self.phi1.id] = "reg13"
        self.v14.alloc[self.phi2.id] = "reg14"
        self.v12.alloc[self.phi2.id] = "reg12"
        phi.eliminate_phi_in_bb(self.bb2)

        # We had 3 basic blocks so the new one should be "bb4"
        self.assertIn("bb4", self.f.bblocks)
        bb4 = self.bb1.succs["bb4"]
        self.assert_edge(self.bb1, bb4)
        self.assert_edge(bb4, self.bb2)
        self.assert_no_edge(self.bb1, self.bb2)


