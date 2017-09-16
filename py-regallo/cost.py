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

    # Computes cost difference cost(f1) - cost(f2)
    def function_diff(self, f1, f2):
        return self.function_cost(f1) - self.function_cost(f2)


# Calculates how many spill instructions (i.e. store nad laod)
# are in provided function, basic block or instruction.
class SpillInstructionsCounter(CostCalculator):
    def __init__(self, name="No. of spill instructions"):
        self.name = name

    def instr_cost(self, instr):
        if instr.opname == cfg.Instruction.LOAD or instr.opname == cfg.Instruction.STORE:
            return 1
        return 0

    def bb_cost(self, bb):
        total = 0
        for instr in bb.instructions:
            total += self.instr_cost(instr)
        return total

    def function_cost(self, f):
        total = 0
        for bb in f.bblocks.values():
            total += self.bb_cost(bb)
        return total


# This is the main cost calculator which for every instruction
# computes L^(loop_depth) * {S - if instruction is store or load, N - otherwise}
# For basic blocks it returns the sum of instructions cost, for functions - the sum
# of costs from all basic blocks.
class MainCostCalculator(CostCalculator):
    def __init__(self, S=2, N=1, L=10, name=None):
        self.S = S # spill
        self.N = N # normal
        self.L = L # loop
        if name is None:
            self.name = "Main cost (S={}, N={}, L={})".format(S, N, L)
        else:
            self.name = name

    def instr_cost(self, instr):
        # Redundant instructions are moves between variables with the same register assigned.
        if instr.is_redundant():
            return 0

        loop_depth = math.pow(self.L, instr.get_loop_depth())

        if instr.opname == cfg.Instruction.LOAD or instr.opname == cfg.Instruction.STORE:
            return self.S * loop_depth
        
        return self.N * loop_depth

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

