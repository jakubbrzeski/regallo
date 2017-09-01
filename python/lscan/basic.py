from sortedcontainers import SortedSet
from lscan import LinearScan
from intervals import Interval, update
import sys
import utils
import cfg
import phi


class BasicLinearScan(LinearScan):
    NAME = "Basic Linaear Scan"

    # Returns dictionary {variable-id: Interval}
    def compute_intervals(self):
        intervals = {v.id: Interval(v) for v in self.f.vars.values()}

        for bb in self.bbs[::-1]:
            for instr in bb.instructions[::-1]:
                # Definition.
                iv = intervals[instr.definition.id]
                update(iv, instr, instr)
                iv.defn = instr
                
                # Uses.
                if instr.is_phi():
                    for (bid, use) in instr.uses.iteritems():
                        iv = intervals[use.id]
                        pred = self.f.bblocks[bid]
                        update(iv, pred.last_instr(), pred.last_instr())
                        # We update interval only to the end of the predecessor block,
                        # not including the current phi instruction. However, we record
                        # that the variable was used here to insert spill instructions
                        # properly later.
                        iv.uses.append(instr)
                else:
                    for use in instr.uses:
                        iv = intervals[use.id]
                        update(iv, instr, instr) # Try extend interval on both sides.
                        iv.uses.append(instr)


            # If the current basic block is a loop header, for all variables that are in 
            # its live-in set we must extend their interval for the whole loop.
            if bb.is_loop_header():
                start = bb.loop.header.first_instr()
                end = bb.loop.tail.last_instr()
                for v in bb.live_in:
                    update(intervals[v.id], start, end)
        
        # For generality:
        return {vid: [iv] for (vid,iv) in intervals.iteritems() if not iv.empty()}

    def allocate_registers(self, intervals, regcount):
        sorted_intervals = sorted([ivl[0] for ivl in intervals.values()], key = lambda iv: iv.fr.num)
        regset = utils.RegisterSet(regcount) # -2?
        active = SortedSet(key = lambda iv: iv.to.num)

        def expire_old_intervals(current):
            for iv in active:
                if iv.to.num > current.fr.num:
                    return
                active.remove(iv)
                regset.set_free(iv.alloc)

        def spill_at_interval(current):
            if active:
                spilled = active[-1] # Active interval with furthest endpoint.
                if spilled.to.num > current.to.num:
                    current.allocate(spilled.alloc)
                    spilled.spill()
                    active.remove(spilled)
                    active.add(current)
                    return
                
            current.spill()

        # LinearScan main loop.
        for iv in sorted_intervals:
            expire_old_intervals(iv)
            reg = regset.get_free()
            if reg:
                iv.allocate(reg)
                active.add(iv)
            else:
                spill_at_interval(iv)

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




