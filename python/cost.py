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
    NAME = "Spill Ratio"
    def instr_cost(self, instr, percent=True):
        assert not instr.is_phi()
        total = 0
        spilled = 0
        for use in instr.uses:
            if instr.id in use.alloc:
                total += 1
                if not utils.is_regname(use.alloc[instr.id]) \
                        or use.alloc[instr.id] == utils.scratch_reg():
                    spilled += 1

        if percent:
            return (spilled * 100) / total

        return (total, spilled)

    def bb_cost(self, bb, percent=True):
        total = 0
        spilled = 0
        for instr in bb.instructions:
            (t,s) = self.instr_cost(instr, percent=False)
            total += t
            spilled += s

        if percent:
            return (spilled * 100) / total

        return (total, spilled)

    def function_cost(self, f, percent=True):
        total = 0
        spilled = 0
        for bb in f.bblocks.values():
            (t, s) = self.bb_cost(bb, percent=False)
            total += t
            spilled += s

        if percent:
            return (spilled * 100) / total

        return (total, spilled)

        

class BasicCostCalculator(CostCalculator):
    NAME = "BASIC"
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



#def compute(f, allocator, cost_calculator, regcount):
#    allocator.full()
