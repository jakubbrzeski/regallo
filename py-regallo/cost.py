import math
import cfg
import utils

class CostCalculator():
    def instr_cost(self, instr):
        raise NotImplementedError()

    def bb_cost(self, bb):
        raise NotImplementedError()

    def function_cost(self, f):
        raise NotImplementedError()

# Only for programs after PHI elimination.
class SpillRatioCalculator(CostCalculator):

    def __init__(self, name="Spill Ratio"):
        self.name = name

    def instr_cost(self, instr, percent=True):
        assert not instr.is_phi()
        if instr.is_redundant():
            return (0, 0)

        total = 0
        spilled = 0
        for use in instr.uses:
                total += 1
                if use.is_spilled():
                    spilled += 1

        if percent:
            return (spilled * 100) / max(1, total)

        return (total, spilled)

    def bb_cost(self, bb, percent=True):
        total = 0
        spilled = 0
        for instr in bb.instructions:
            (t,s) = self.instr_cost(instr, percent=False)
            total += t
            spilled += s

        if percent:
            return (spilled * 100) / max(1, total)

        return (total, spilled)

    def function_cost(self, f, percent=True):
        total = 0
        spilled = 0
        for bb in f.bblocks.values():
            (t, s) = self.bb_cost(bb, percent=False)
            total += t
            spilled += s

        if percent:
            return (spilled * 100) / max(1, total)

        return (total, spilled)

        
# Sum of l^(loop_depth) * instruction_cost,
# where instruction_cost = s if instruction is LOAD or SPILL
#                        = n otherwise
class BasicCostCalculator(CostCalculator):

    def __init__(self, s=2, n=1, l=10, name=None):
        self.s = s # spill
        self.n = n # normal
        self.l = l # loop
        if name is None:
            self.name = "Default ({}, {}, {})".format(s, n, l)
        else:
            self.name = name

    def instr_cost(self, instr):
        if instr.is_redundant():
            return 0

        loop_depth = math.pow(self.l, instr.get_loop_depth())

        if instr.opname == cfg.Instruction.LOAD or instr.opname == cfg.Instruction.STORE:
            return self.s * loop_depth
        
        return self.n * loop_depth

    def bb_cost(self, bb):
        res = 0
        for instr in bb.instructions:
            res += self.instr_cost(instr)

        return res

    def function_cost(self, f):
        res = 0
        for bb in f.bblocks.values():
            res += self.bb_cost(bb)

        return res

