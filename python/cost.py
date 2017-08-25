import math
import cfg

class BasicCostCalculator:
    def instr_cost(self, instr):
        loop_depth = math.pow(10, instr.get_loop_depth())
        if instr.opname == cfg.Instruction.LOAD:
            return 2 * loop_depth
        elif instr.opname == cfg.Instruction.STORE:
            return 2 * loop_depth
        else:
            return loop_depth

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



