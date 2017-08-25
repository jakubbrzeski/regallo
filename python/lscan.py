import utils
import cfg
import cfgprinter
from sortedcontainers import SortedSet

class Interval:
    class SubInterval:
        def __init__(self, fr, to, parent):
            self.fr = fr
            self.to = to
            self.parent = parent # Parent interval.

    def __init__(self, var, fr=None, to=None, alloc=None, defn=None, uses=None):
        # Variable this interval represents
        self.var = var
        # Instructions this interval starts and ends with.
        self.fr = fr
        self.to = to
        # Allocated allocister
        self.alloc = alloc
        # Note that it doesn't always need to be the same as self.fr.
        self.defn = defn
        # List of instructions which use self.var in this interval.
        self.uses = [] if uses is None else uses
        # Stack (list) of subintervals.
        self.subintervals = []
        # Dictionary {instruction-id: alloc} denoting what
        # allocister the variable was allocated to in the
        # given instruction.
        self.instr_to_alloc = {}

    def add_subinterval(self, fr, to):
        siv = Interval.SubInterval(fr, to, self)
        self.subintervals.append(siv)
        return siv

    def empty(self):
        return self.fr == self.to

    def get_last(self):
        if self.empty():
            return None
        return self.subintervals[-1]

    def update_variables(self, alloc):
        if self.defn is not None:
            self.var.alloc[self.defn.id] = alloc
        for use in self.uses:
            self.var.alloc[use.id] = alloc

    def allocate(self, alloc):
        self.alloc = alloc
        self.update_variables(alloc)

    def spill(self):
        print "spill variable", self.var.id
        self.alloc = utils.slot(self.var)
        self.update_variables(self.alloc)


class BasicLinearScan:
    def __init__(self, f, bbs_list = None):
        self.f = f

        # This is dictionary of intervals. Each variable may have more then one interval,
        # e.g. after splitting or when we consider holes in the intervals or when we break
        # SSA form. That's why we keep a list of SubIntervals for each variable id.
        self.intervals = {}

        self.bbs = bbs_list
        if bbs_list is None:
            # We want to browse the basic blocks backwards.
            # Postorder guarantees that if a DOM> b, we will visit
            # b first. 
            self.bbs = utils.reverse_postorder(f)

        utils.number_instructions(self.bbs)


    # Returns dictionary {variable-id: Interval}
    def compute_intervals(self, print_debug=False):
        utils.number_instructions(self.bbs)
        intervals = {v.id: Interval(v) for v in self.f.vars.values()}

        def update(iv, fr, to):
            if iv.fr is None or iv.fr.num > fr.num:
                iv.fr = fr
            if iv.to is None or iv.to.num < to.num:
                iv.to = to

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
            spilled = active[-1] # Active interval with furthest endpoint.
            if spilled.to.num > current.to.num:
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
            else: 
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

        
"""
    def allocate_registers(self, intervals, register_count):
        # We reserve two registers for spilling.
        regset = utils.RegisterSet(register_count-2)
        dummy_def = self.f.get_or_create_variable()

        class Action:
            START = 1
            END = -1
            def __init__(self, num, kind, siv):
                self.num = num
                self.kind = kind
                self.siv = siv

            def is_subinterval_end(self):
                return self.kind == self.END

        actions = SortedSet(key = lambda action: (action.num, action.kind))

        for ivlist in intervals.values():
            # In basic lscan there is only one interval per variable.
            for siv in ivlist[0].subintervals:
                actions.add(Action(siv.num_from(), Action.START, siv))
                actions.add(Action(siv.num_to(), Action.END, siv))

        instr_before = {}
        instr_after = {} 

        def spill_current(active, inactive, siv):
            return (siv.parent, None)

        spill_choose = spill_current
        
        # List of subintervals that need to be spilled.
        to_spill = []
        for action in actions:
            siv = action.siv
            print "action:", action.kind, action.num, cfgprinter.value_str(siv.parent.var)
            # If the subinterval ends, we don't need its register anymore.
            if action.is_subinterval_end():
                del active[siv.parent.var.id]
                inactive[siv.parent.var.id] = siv.parent

                if siv.parent.reg:
                    regset.set_free(siv.parent.reg)
                # else: interval was spilled.

            else:
                reg = regset.get_free()

                if reg is None:
                    (iv_to_spill, endpoint) = spill_choose(active, inactive, siv)
                    if iv_to_spill
                  
                else:

                    # We allocate the free register to this interval.
                    siv.parent.reg = reg



        # Rewrite all spilled intervals: delete all that were marked so.
        for iv in intervals.values():
            iv.batch_delete()

        


        # Return allocated intervals.
        return intervals
    """
'''
elif instr.definition in instr.live_out:
                    # It may happen that we will come across the variable's definition before
                    # any use, e.g. when the variable is defined inside a loop and is used by
                    # phi function in the loop header.
                    siv = intervals[instr.definition.id].add_subinterval(instr, instr)
                    siv.defn = instr
'''
"""
    def split_interval(self, iv, fr, to):
        rev_sivs = iv.subintervals[::-1]
        
        siv_start = None
        siv_end = None
        take = []
        stay_start = []
        stay_end = []
        for siv in rev_sivs:
            if siv.fr.num < fr.num and fr.num <= siv.to.num:
                siv_start = siv
            elif fr.num <= siv.fr.num and siv.to.num <= to.num:
                take.append(siv)
            elif siv.fr.num <= to.num and to.num < siv.to.num:
                siv_end = siv
            elif siv.to.num < fr.num:
                stay_start.append(siv)
            elif siv.fr.num > to.num:
                stay_end.append(siv)

        prev = self.num_to_instr[fr.num-1]
        nxt = self.num_to_instr[to.num+1]
        sivs_stay = []
        sivs_stay.extend(sivs_stay_start)
        if siv_start:
            # new subintervals: a = [siv_start.fr, prev], b =[fr, siv_start.to] 
            uses_a = []
            uses_b = []
            for use in siv_start.uses:
                if use.num <= prev.num:
                    uses_a.append(use)
                else:
                    uses_b.append(use)
            
    
            if siv_start is siv_end:
                # [3, 10] -> [5,8]
"""
                   
"""
    def split_interval(self, iv, fr, to):
        rev_sivs = iv.subintervals[::-1]
        
        siv_start = None
        siv_end = None
        take = []
        stay_start = []
        stay_end = []
        for siv in rev_sivs:
            if siv.fr.num < fr.num and fr.num <= siv.to.num:
                siv_start = siv
            elif fr.num <= siv.fr.num and siv.to.num <= to.num:
                take.append(siv)
            elif siv.fr.num <= to.num and to.num < siv.to.num:
                siv_end = siv
            elif siv.to.num < fr.num:
                stay_start.append(siv)
            elif siv.fr.num > to.num:
                stay_end.append(siv)

        prev = self.num_to_instr[fr.num-1]
        nxt = self.num_to_instr[to.num+1]
        sivs_stay = []
        sivs_stay.extend(sivs_stay_start)
        if siv_start:
            # new subintervals: a = [siv_start.fr, prev], b =[fr, siv_start.to] 
            uses_a = []
            uses_b = []
            for use in siv_start.uses:
                if use.num <= prev.num:
                    uses_a.append(use)
                else:
                    uses_b.append(use)
            
    
            if siv_start is siv_end:
                # [3, 10] -> [5,8]
"""

