from sortedcontainers import SortedSet
from lscan import LinearScan
from intervals import Interval
import sys
import utils
import cfg
import phi


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
                

    def allocate_registers(self, intervals, regcount):
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
                self.spill_at_interval(iv, active)

    # Checks all intervals that were spilled (don't have register assigned),
    # and inserts load and store instructions in appropriate places of the program.
    # IMPORTANT: it doesn't insert spill code for variables in phi instructions.
    #            it is done separately in phi elimination phase.
    # WARNING: it breaks uevs, defs and liveness sets and loop information.
    def insert_spill_code(self, intervals):
        dummy_def = self.f.get_or_create_variable()
        insert_after = {iid: [] for iid in range(self.f.instr_counter)}
        insert_before = {iid: [] for iid in range(self.f.instr_counter)}
        update_endpoint = []
        for vid in intervals.keys():
            iv = intervals[vid][0]
            if utils.is_slotname(iv.alloc):
                # We divide iv into several small of the form: [def, store] and [load, use]
                ivlist = []
                
                slot = iv.alloc
                if iv.defn and not iv.defn.is_phi():
                    store = cfg.Instruction(iv.defn.bb, None, cfg.Instruction.STORE,
                                [iv.var], [slot, iv.var])
                    
                    insert_after[iv.defn.id].append(store)
                    iv.var.alloc[iv.defn.id] = utils.scratch_reg()
                    iv.var.alloc[store.id] = utils.scratch_reg()
                    ivlist.append(Interval(iv.var, iv.defn, store, None, iv.defn, [store]))
                    
                for instr in iv.uses:
                    if not instr.is_phi():
                        load = cfg.Instruction(instr.bb, iv.var, cfg.Instruction.LOAD, [], 
                                [slot])
                        iv.var.alloc[instr.id] = utils.scratch_reg()
                        iv.var.alloc[load.id] = utils.scratch_reg()
                        insert_before[instr.id].append(load)

                        new_iv = Interval(iv.var, load, instr, None, load, [instr])
                        ivlist.append(new_iv)
                
                intervals[vid] = ivlist
        
        # Reewrite instructions.
        for bb in self.f.bblocks.values():
            new_instructions = []
            for instr in bb.instructions:
                for ib in insert_before[instr.id]:
                    new_instructions.append(ib)
                new_instructions.append(instr)
                for ia in insert_after[instr.id]:
                    new_instructions.append(ia)

            bb.set_instructions(new_instructions)

        for (iv, pred) in update_endpoint:
            iv.to = pred.last_instr()

        # Because new instructions were inserted we have to renumber
        # all instructions.
        utils.number_instructions(self.bbs)

    def resolve(self, intervals):
        self.insert_spill_code(intervals)
        phi.eliminate_phi(self.f)




