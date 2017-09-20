from sortedcontainers import SortedSet
from allocators.lscan import LinearScan
from allocators.lscan.intervals import Interval
import spillers
import sys
import utils
import cfg

class BasicLinearScan(LinearScan):
    def __init__(self, spiller=spillers.default(), name="Basic Linear Scan"):
        super(BasicLinearScan, self).__init__(name)
        self.spiller = spiller

    # Returns dictionary {variable-id: [Interval]}
    # For generality, we return list of a single Interval because in other
    # versions of the algorithm (see ExtendedLinearScan) multiple intervals
    # for one variable may appear.
    def compute_intervals(self, f):
        intervals = {v.id: Interval(v) for v in f.vars.values()}
        bbs = utils.reverse_postorder(f)
        utils.number_instructions(bbs)

        # Intervals always start from definition. If a variable is defined in a loop
        # and used in a phi instruction at the loop header, its interval ends at the
        # end of the loop..
        for bb in bbs[::-1]:
            for v in bb.live_out:
                iv = intervals[v.id]
                if iv.to < bb.last_instr().num + 0.5:
                    iv.to = bb.last_instr().num + 0.5
                iv.fr = bb.first_instr().num - 0.5

            for instr in bb.instructions[::-1]:
                # Definition.
                if instr.definition and not instr.definition.is_spilled():
                    iv = intervals[instr.definition.id]
                    iv.defn = instr
                    if not instr.is_phi():
                        iv.fr = instr.num 
                
                # Uses.
                if instr.is_phi():
                    for (bid, var) in instr.uses.iteritems():
                        if not var.is_spilled():
                            iv = intervals[var.id]
                            pred = f.bblocks[bid]
                            if iv.to < pred.last_instr().num + 0.5:
                                iv.to = pred.last_instr().num + 0.5
                            # We update interval only to the end of the predecessor block,
                            # not including the current phi instruction. However, we record
                            # that the variable was used here.
                            iv.uses.append(instr)
                else:
                    for var in instr.uses:
                        if not var.is_spilled():
                            iv = intervals[var.id]
                            if iv.to < instr.num:
                                iv.to = instr.num
                            iv.uses.append(instr)

        # We skip empty intervals.
        return {vid: [iv] for (vid,iv) in intervals.iteritems() if not iv.empty()}

    
    def allocate_registers(self, intervals, regcount, spilling=True):
        sorted_intervals = sorted([ivl[0] for ivl in intervals.values()], 
                key = lambda iv: iv.fr)
        regset = utils.RegisterSet(regcount)
        active = SortedSet(key = lambda iv: iv.to)
        spill_occurred = False

        def expire_old_intervals(current):
            for iv in active:
                if iv.to > current.fr:
                    return
                active.remove(iv)
                regset.set_free(iv.alloc)

        # LinearScan main loop.
        for iv in sorted_intervals:
            expire_old_intervals(iv)
            reg = regset.get_free()
            if reg:
                iv.allocate(reg)
                active.add(iv)
            elif not spilling:
                return False
            else:
                self.spiller.spill_at_interval(iv, active)
                spill_occurred = True
            
        if not spill_occurred:
            return True

        return False


    def resolve(self, intervals):
        pass

