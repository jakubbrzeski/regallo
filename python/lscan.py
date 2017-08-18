import utils
import cfg
import cfg_pretty_printer as cfgprinter
from sortedcontainers import SortedSet


class Interval:

    class SubInterval:
        def __init__(self, fr, to, parent):
            # Instructions this interval starts and ends with.
            self.fr = fr
            self.to = to
            # Note that it doesn't always need to be the same as self.fr.
            self.defn = fr
            # List of instructions which use self.var in this interval.
            self.uses = [to]
            # Parent interval list.
            self.parent = parent
            # If True, is should be deleted from the interval list of self.var.
            # It's useful when the variable is spilled and we want to replace
            # the continuous interval with multiple small intervals.
            self.delete = False

        def is_open(self):
            return self.fr is None

        # Get number of instruction this interval starts from.
        def num_from(self):
            if self.fr:
                return self.fr.num
            return -1

        # Get number of instruction this interval ends at.
        def num_to(self):
            if self.to:
                return self.to.num
            return -1

    def __init__(self, var):
        self.var = var
        # Allocated register
        self.reg = None
        # Stack (list) of subintervals.
        self.subintervals = []
        # Dictionary {instruction-id: reg} denoting what
        # register the variable was allocated to in the
        # given instruction.
        self.instr_to_reg = {}

    def add_subinterval(self, fr, to):
        siv = self.SubInterval(fr, to, self)
        self.subintervals.append(siv)
        return siv

    def update_last(self, fr, to):
        siv = self.subintervals[-1]
        if siv.fr is None or siv.fr.num > fr.num:
            siv.fr = fr
        if siv.to is None or siv.to.num < to.num:
            siv.to = to

    def is_empty(self):
        return len(self.subintervals) == 0

    def get_last(self):
        if self.is_empty():
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

        # Dictionary {instr-id: number of instruction} in the order of basic blocks.
        self.num = utils.number_instructions(self.bbs)


    # Returns dictionary {variable-id: Interval}
    def compute_intervals(self, print_debug=False):
        utils.number_instructions(self.bbs)
        intervals = {v.id: Interval(v) for v in self.f.vars.values()}

        for bb in self.bbs[::-1]:
            if print_debug:
                print "Basic block", cfgprinter.value_str(bb)

            for instr in bb.instructions[::-1]:
                # Definition.
                # End the open interval and set interval's defn. 
                # There might be no open interval if the variable is not used anywhere.
                last_siv = intervals[instr.definition.id].get_last()
                if last_siv:
                    if last_siv.is_open() or last_siv.num_from() > instr.num:
                        last_siv.fr = last_siv.defn = instr
                        if print_debug:
                            print "  End interval:", cfgprinter.value_str(instr.definition)

                # Uses.
                # If there is an open interval (with no definition found yet), add
                # this instruction to interval's use list. Otherwise, create a new interval
                # for this variable which ends at this instruction.
                for use in instr.uses:
                    last_siv = intervals[use.id].get_last()
                    if last_siv and last_siv.is_open():
                        last_siv.uses.append(instr)
                        if print_debug:
                            print "  Add use to open interval:", cfgprinter.value_str(use)
                    else:
                        siv = intervals[use.id].add_subinterval(None, instr)
                        if print_debug:
                            print "  Create new interval:", cfgprinter.value_str(use)
                        
            # If the current basic block is a loop header, for all variables that are in 
            # its live-in set we must extend their interval for the whole loop.
            if bb.is_loop_header():
                start = bb.loop.header.instructions[0]
                end = bb.loop.tail.instructions[-1]
                for v in bb.live_in:
                    intervals[v.id].update_last(start, end)
                    if print_debug:
                        print " Extending interval for loop:", cfgprinter.value_str(v)


        return intervals
                    


    def allocate_registers(self, intervals, register_count):
        # We reserve two registers for spilling.
        regset = utils.RegisterSet(register_count-2)

        # We create a dummy variable for 'store' instruction definition that will not
        # be used anywhere but is neccessary because each instruction must have definition
        # Variable.
        dummy_store_def = self.f.get_or_create_variable()

        # We need a sorted list of actions on intervals:
        # (from, 1, SubInterval) - beginning of the interval.
        # (to, -1, SubInterval) - end of the interval.
        # This way, for multiple interval endpoints at the same instruction we
        # will process endings first.

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

        for iv in intervals.values():
            for siv in iv.subintervals:
                actions.add(Action(siv.num_from(), Action.START, siv))
                actions.add(Action(siv.num_to(), Action.END, siv))

        # When we spill variables, we need to insert stores and loads in some parts
        # of the program. Similarly, we may need to add moves to get rid of SSA form
        # at the end etc. Instead of inserting those instructions immediately, we record
        # them in the dictionaries in order to rewrite the whole program at the end.
        # It is more efficient because insertion to the list is linear and in case of
        # many insertions it will take a lot of time.
        # These are dictionaries {instruction-id: list of Instructions} and denote
        # list of new instructions to insert before or after specific instruction.
        instr_before = {iid: [] for iid in range(0, self.f.instr_counter)}
        instr_after = {iid: [] for iid in range(0, self.f.instr_counter)}

        for action in actions:
            siv = action.siv
            print "action:", action.kind, action.num, cfgprinter.value_str(siv.parent.var)
            # If the subinterval ends, we don't need its register anymore.
            if action.is_subinterval_end():
                if siv.parent.reg:
                    # In basic linear scan intervals don't have holes so during register
                    # allocation interval should be composed of one subinterval.
                    regset.set_free(siv.parent.reg)
                    print "  > subinterval end, set free", cfgprinter.value_str(siv.parent.reg)
                else:
                    print "  > subinterval end, was spilled, do nothing. "

            else:
                print "  > subinterval start, try allocate register"
                # When we come across a new interval, we try to reserve a free register for it.
                reg = regset.get_free()

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
                if reg is None:
                    print "  >>> No register available, spilling", \
                            cfgprinter.value_str(siv.parent.var), "in [", \
                            siv.num_from(), ",", siv.num_to(), "]"
                  
                    # Mark this interval for deletion because after insertions of
                    # stores and loads,  we have to replace it with new intervals.
                    # In actions there is still another endpoint of this interval
                    # but will be skipped in the loop due to lack of register allocated.
                    siv.delete = True

                    if siv.defn:
                        store = cfg.Instruction(
                                    self.f.get_free_iid(),
                                    siv.defn.bb,
                                    dummy_store_def,
                                    cfg.Instruction.STORE,
                                    [siv.parent.var],
                                    uses_debug=[siv.parent.var.id])

                        instr_after[siv.defn.id].append(store)
                        new_siv = siv.parent.add_subinterval(siv.defn, store)

                    
                    for use in siv.uses:
                        load = cfg.Instruction(
                                self.f.get_free_iid(),
                                use.bb,
                                siv.parent.var,
                                cfg.Instruction.LOAD,
                                [], uses_debug=["const"])

                        instr_before[use.id].append(load)
                        print "dupa"
                        new_siv = siv.parent.add_subinterval(load, use)


                else:
                    print "  >>> OK, allocating", \
                            cfgprinter.value_str(siv.parent.var), \
                            "in [", siv.num_from(), ",", siv.num_to(), "] to", \
                            cfgprinter.value_str(reg)

                    # We allocate the free register to this interval.
                    siv.parent.reg = reg


        # Rewrite all spilled intervals: delete all that were marked so.
        for iv in intervals.values():
            iv.batch_delete()

        # Reewrite instructions.
        for bb in self.f.bblocks.values():
            new_instructions = []
            for instr in bb.instructions:
                for ib in instr_before[instr.id]:
                    new_instructions.append(ib)
                new_instructions.append(instr)
                for ia in instr_after[instr.id]:
                    new_instructions.append(ia)

            bb.set_instructions(new_instructions)

        # Because new instructions were inserted we have to renumber
        # all instructions and recompute liveness sets.
        utils.number_instructions(self.bbs)
        self.f.compute_defs_and_uevs()
        self.f.perform_liveness_analysis()

        # Return allocated intervals.
        return intervals


