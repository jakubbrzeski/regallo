import utils
import cfg
import cfg_pretty_printer as cfgprinter
from sortedcontainers import SortedSet


class Interval:

    class SubInterval:
        def __init__(self, fr, to, parent):
            self.fr = fr
            self.to = to
            # Parent interval.
            self.parent = parent

    def __init__(self, var, fr=None, to=None, reg=None, defn=None, uses=None):
        # Variable this interval represents
        self.var = var
        # Instructions this interval starts and ends with.
        self.fr = fr
        self.to = to
        # Allocated register
        self.reg = reg
        # Note that it doesn't always need to be the same as self.fr.
        self.defn = defn
        # List of instructions which use self.var in this interval.
        self.uses = [] if uses is None else uses
        # Stack (list) of subintervals.
        self.subintervals = []
        # Dictionary {instruction-id: reg} denoting what
        # register the variable was allocated to in the
        # given instruction.
        self.instr_to_reg = {}

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

    # Rewrites list of intervals skipping all marked to be deleted.
    def batch_delete(self):
        new_subintervals = []
        for siv in self.subintervals:
            if not siv.delete:
                new_subintervals.append(siv)

        self.subintervals = new_subintervals

        
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

        self.num_to_instr = utils.number_instructions(self.bbs)


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
                for use in instr.uses:
                    iv = intervals[use.id]
                    update(iv, instr, instr) # Try extend interval on both sides.
                    iv.uses.append(instr)


            # If the current basic block is a loop header, for all variables that are in 
            # its live-in set we must extend their interval for the whole loop.
            if bb.is_loop_header():
                start = bb.loop.header.instructions[0]
                end = bb.loop.tail.instructions[-1]
                for v in bb.live_in:
                    update(intervals[v.id], start, end)
        
        # For generality:
        return {vid: [iv] for (vid,iv) in intervals.iteritems() if not iv.empty()}
                    
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

    def allocate_registers(self, intervals, regcount):
        sorted_intervals = sorted([ivl[0] for ivl in intervals.values()], key = lambda iv: iv.fr.num)
        regset = utils.RegisterSet(regcount) # -2?
        active = SortedSet(key = lambda iv: iv.to.num)

        def expire_old_intervals(current):
            for iv in active:
                if iv.to.num > current.fr.num:
                    return
                active.remove(iv)
                regset.set_free(iv.reg)

        def spill_at_interval(current):
            spilled = active[-1] # Active interval with furthest endpoint.
            if spilled.to.num > current.to.num:
                current.reg = spilled.reg
                spilled.reg = None
                active.remove(spilled)
                active.add(current)
            # else: we do nothing, current.reg is not assigned a register so
            # it means it will be spilled.
        
        # LinearScan main loop.
        for iv in sorted_intervals:
            expire_old_intervals(iv)
            reg = regset.get_free()
            if reg:
                iv.reg = reg
                active.add(iv)
            else:
                spill_at_interval(iv)


    def insert_spill_code(self, intervals):
        dummy_store_def = self.f.get_or_create_variable()
        insert_after = {iid: [] for iid in range(self.f.instr_counter)}
        insert_before = {iid: [] for iid in range(self.f.instr_counter)}
        for vid in intervals.keys():
            iv = intervals[vid][0]
            if iv.reg is None:
                # We divide iv into several small of the form: [def, store] and [load, use]
                ivlist = []
                
                if iv.defn:
                    store = cfg.Instruction(
                                self.f.get_free_iid(),
                                iv.defn.bb,
                                dummy_store_def,
                                cfg.Instruction.STORE,
                                [iv.var],
                                uses_debug=[iv.var.id])
                    
                    insert_after[iv.defn.id].append(store)
                    # TODO: reg?
                    ivlist.append(Interval(iv.var, iv.defn, store, None, iv.defn, [store]))
                    
                for use in iv.uses:
                    load = cfg.Instruction(
                                self.f.get_free_iid(),
                                use.bb,
                                iv.var,
                                cfg.Instruction.LOAD,
                                [], uses_debug=["const_addr"])

                    if use.is_phi():
                        # insert at the end of the predecessor block
                        pred_id = use.phi_preds[iv.var.id]
                        pred = use.bb.preds[pred_id]
                        insert_after[pred.instructions[-1].id].append(load)
                    else:
                        insert_before[use.id].append(load)

                    # TODO: reg?
                    ivlist.append(Interval(iv.var, load, use, None, load, [use]))
                
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


        # Because new instructions were inserted we have to renumber
        # all instructions and recompute liveness sets.
        utils.number_instructions(self.bbs)
        self.f.compute_defs_and_uevs()
        self.f.perform_liveness_analysis()

    """
    def allocate_registers(self, intervals, register_count):
        # We reserve two registers for spilling.
        regset = utils.RegisterSet(register_count-2)
        dummy_store_def = self.f.get_or_create_variable()

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
# When we spill variables, we need to insert stores and loads in some parts
# of the program. Similarly, we may need to add moves to get rid of SSA form
# at the end etc. Instead of inserting those instructions immediately, we record
# them in the dictionaries in order to rewrite the whole program at the end.
# It is more efficient because insertion to the list is linear and in case of
# many insertions it will take a lot of time.
# These are dictionaries {instruction-id: list of Instructions} and denote
# list of new instructions to insert before or after specific instruction.


# If there is no free register, we need to spill variable on this
# interval (not the whole program). It boils down to inserting 'store' 
# after variable's definition and 'loads' before each use. Because of
# new instructions, We also have to replace the current interval with new, 
# small intervals: [definition, store] and [load, use] for each use.
#
# Important thing to notice is that loads generate new definitions and
# we reuse the same variable in all theses definitions, which breaks SSA form.
# However, we insert the stores and loads only after register allocation, 
# and then we already don't care about SSA.
#
# Moreover, we use a dummy variable for store instruction deifinition.
# This variable will not be used anywhere and will not generate any intervals,
# so will not have to be granted any register.

'''
elif instr.definition in instr.live_out:
                    # It may happen that we will come across the variable's definition before
                    # any use, e.g. when the variable is defined inside a loop and is used by
                    # phi function in the loop header.
                    siv = intervals[instr.definition.id].add_subinterval(instr, instr)
                    siv.defn = instr
'''
