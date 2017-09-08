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

    # Returns dictionary {variable-id: Interval}
    def compute_intervals(self, f):
        intervals = {v.id: Interval(v) for v in f.vars.values()}
        bbs = utils.reverse_postorder(f)
        utils.number_instructions(bbs)

        for bb in bbs[::-1]:
            for instr in bb.instructions[::-1]:
                # Definition.
                if instr.definition:
                    iv = intervals[instr.definition.id]
                    iv.update_endpoints(instr.num, instr.num)
                    iv.defn = instr
                
                # Uses.
                if instr.is_phi():
                    for (bid, var) in instr.uses.iteritems():
                        iv = intervals[var.id]
                        pred = f.bblocks[bid]
                        iv.update_endpoints(pred.last_instr().num, pred.last_instr().num)
                        # We update interval only to the end of the predecessor block,
                        # not including the current phi instruction. However, we record
                        # that the variable was used here e.g. to insert spill instructions
                        # properly later.
                        iv.uses.append(instr)
                else:
                    for var in instr.uses:
                        iv = intervals[var.id]
                        iv.update_endpoints(instr.num, instr.num)
                        iv.uses.append(instr)


            # If the current basic block is a loop header, for all variables that are in 
            # its live-in set we must extend their interval for the whole loop.
            if bb.is_loop_header():
                start = bb.loop.header.first_instr()
                end = bb.loop.tail.last_instr()
                for v in bb.live_in:
                    iv.update_endpoints(start.num, end.num)
        
        # For generality:
        return {vid: [iv] for (vid,iv) in intervals.iteritems() if not iv.empty()}

    
    def allocate_registers(self, intervals, regcount, spilling=True):
        sorted_intervals = sorted([ivl[0] for ivl in intervals.values()], 
                key = lambda iv: iv.fr)
        regset = utils.RegisterSet(regcount)
        active = SortedSet(key = lambda iv: iv.to)

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

        return True


    def resolve(self, intervals):
        pass


    def full_allocation(self, f, regcount, spilling=True):
        ivs = self.compute_intervals(f)
        success = self.allocate_registers(ivs, regcount, spilling)
        if not success:
            return False
        self.resolve(ivs)
        return True



