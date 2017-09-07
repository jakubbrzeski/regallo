from sortedcontainers import SortedSet
from lscan import LinearScan
from intervals import Interval
import sys
import utils
import cfg


class BasicLinearScan(LinearScan):
    NAME = "Basic Linaear Scan"

    class SpillingStrategy(object):
        FURTHEST_FIRST, CURRENT_FIRST, LESS_USED_FIRST = range(3)


    def __init__(self, **kwargs):
        super(BasicLinearScan, self).__init__()
        self.spilling_strategy = kwargs.get("spilling_strategy", 
                BasicLinearScan.SpillingStrategy.FURTHEST_FIRST)


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
                    for (bid, use) in instr.uses.iteritems():
                        iv = intervals[use.id]
                        pred = f.bblocks[bid]
                        iv.update_endpoints(pred.last_instr().num, pred.last_instr().num)
                        # We update interval only to the end of the predecessor block,
                        # not including the current phi instruction. However, we record
                        # that the variable was used here e.g. to insert spill instructions
                        # properly later.
                        iv.uses.append(instr)
                else:
                    for use in instr.uses:
                        iv = intervals[use.id]
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

    # Decides which interval should be spilled, based on chosen strategy.
    def spill_at_interval(self, current, active):
        if not active or self.spilling_strategy == self.SpillingStrategy.CURRENT_FIRST:
            current.spill()
            return
        
        elif self.spilling_strategy == self.SpillingStrategy.LESS_USED_FIRST:
            spilled = current
            for iv in active:
                if len(iv.uses) < len(spilled.uses):
                    spilled = iv

            if spilled is not current:
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
            else:
                current.spill()

        else: # Furthest first. 
            spilled = active[-1] # Active interval with furthest endpoint.
            if spilled.to > current.to:
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
            else:
                current.spill()
                

    def allocate_registers(self, intervals, regcount, spilling=True):
        sorted_intervals = sorted([ivl[0] for ivl in intervals.values()], 
                key = lambda iv: iv.fr)
        regset = utils.RegisterSet(regcount) # -2?
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
            else:
                if not spilling:
                    return False
                self.spill_at_interval(iv, active)

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



