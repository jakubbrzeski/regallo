import utils
import cfg
import cfg_pretty_printer as cfgprinter

class Interval:
    def __init__(self, var):
        self.fr = -1
        self.to = -1

        # Variable this interval represents.
        self.var = var

        # We need to keep track of definition and uses of the variable in this
        # interval. There may be multiple intervals for the same variable (especially
        # when we use e.g. linear scan with interval holes).
        self.defn = None
        self.uses = []

        # Register allocation assigns registers to intervals which
        # describe a variable in different parts of a program.
        self.reg = None

    def add_range(self, fr, to):
        if fr < self.fr:
            self.fr = fr
        if to > self.to:
            self.to = to

    def allocate(reg):
        self.reg = reg

class BasicLinearScan:
    def __init__(self, f, bbs_list = None):
        self.f = f
        self.intervals = None
        self.bbs = bbs_list
        if bbs_list is None:
            # We want to browse the basic blocks backwards.
            # Postorder guarantees that if a DOM> b, we will visit
            # b first. 
            self.bbs = utils.reverse_postorder(f)

        # Dictionary {instr-id: number of instruction} in the order of basic blocks.
        self.num = utils.number_instructions(self.bbs)

    def compute_intervals(self, print_debug=False):
        # Initialize intervals dictionary.
        intervals = {vid: [] for vid in self.f.vars.keys()}
        
        # In most basic form of the linear scan we use only continuous intervals
        # without holes. 
        for bb in self.bbs[::-1]:
            if print_debug:
                print "Basic block", cfgprinter.value_str(bb)

            for instr in bb.instructions[::-1]:
                # Definition.
                # End the open interval and set interval's defn. 
                # There might be no open interval if the variable is not used anywhere.
                if intervals[instr.definition.id]: # if list not empty
                    iv = intervals[instr.definition.id][-1] # get last
                    if iv.fr == -1 or iv.fr > self.num[instr.id]: # it's an open interval
                        iv.fr = self.num[instr.id]
                        iv.defn = instr
                        if print_debug:
                            print "  Ending interval for", cfgprinter.value_str(instr.definition)

                # Use.
                # - If there is an interval open (with no definition found yet), add
                # this instruction to interval's uses list.
                # - If there is no open interval, create a new one for this variable,
                # which ends at this instruction.
                for use in instr.uses:
                    if intervals[use.id] and intervals[use.id][-1].fr == -1:
                        intervals[use.id][-1].uses.append(use)
                        if print_debug:
                            print "  Add use to open interval for", cfgprinter.value_str(use)
                    else:
                        iv = Interval(use)
                        iv.to = self.num[instr.id]
                        iv.uses.append(instr)
                        intervals[use.id].append(iv)
                        if print_debug:
                            print "  Create new interval for", cfgprinter.value_str(use)
                        
                        
            # If the current basic block is a loop header, for all variables that are in 
            # its live-in set we must extend their interval for the whole loop.
            # It rather relates only to intervals that ends in the middle of the loop.
            if bb.is_loop_header():
                fr = self.num[bb.loop.header.instructions[0].id]
                to = self.num[bb.loop.tail.instructions[-1].id]
                for v in bb.live_in:
                    # if variable is live it must have some interval ?
                    if intervals[v.id][-1].to < to:
                        intervals[v.id][-1].to = to
                    if intervals[v.id][-1].fr == -1 or intervals[v.id][-1].fr > fr:
                        intervals[v.id][-1].fr = fr
                    if print_debug:
                        print "  Extending interval to the whole loop for", cfgprinter.value_str(v)

                

        #for bb in bbs_postorder[::-1]:
        #    print cfgprinter.basic_block_str(bb, instr_nums=num, intervals=intervals,
        #            print_interval_for="v12")

        self.intervals = intervals

    def allocate_registers(regset):
        # We reserve a special register which is used when a variable was spilled
        # to memory. It stores a variable after load to execute the instruction,
        # which uses this variable. It is the same for all variables.
        spill_reg = regset.get_free()

        # A list of actions on intervals:
        # (1, from, Interval) - beginning of the interval.
        # (-1, to, Interval) - end of the interval.
        # This way, for multiple interval endpoints at the same instruction we
        # will process endings first.
        starts = [(1, intval.fr, intval) for intval in self.intervals.values()]
        ends = [(-1, intval.to, intval) for intval in self.intervals.values()]
        actions = sorted(starts + ends, lambda (a,b,c) : (a,b)) # sort by two first coefs

        # When we spill variables, we need to insert stores and loads in some places
        # of the program. Similarly, we may need to add moves to get rid of SSA form
        # at the end etc. Instead of inserting those instructions at once, we record
        # them in the dictionaries in order to rewrite the whole program at the end.
        # It is more efficient because insertion to the list is linear and takes
        # a lot of time in case of many insertions.
        instr_before = {}
        instr_after = {}

        for action in actions:
            (endpoint, num, intval) = action
            if endpoint == -1:
                regset.set_free(intval.reg)

            elif endpoint == 1:
                reg = regset.get_free()

                # If there is no free register, we need to spill variable to memory,
                # i.e. insert 'store' after its definition and all uses and 'loads' 
                # before each use.
                if reg is None:
                    if intval.defn is not None:
                        store = cfg.Instruction(
                                    self.f.get_free_iid(),
                                    intval.defn.bb,
                                    cfg.Instruction.STORE,
                                    intval.var)
                        instr_after[intval.defn.id].append(store)
                    
                    # For each use we load and store value operating on the same variable.
                    # It breaks SSA because we will have multiple definitions
                    # but instructions are inserted after allocation when we
                    # don't need SSA anymore. 
                    for use in intval.uses:
                        load = cfg.Instruction(
                                self.f.get_free_iid(),
                                use.bb,
                                cfg.Instruction.LOAD,
                                intval.var)

                        store = cfg.Instruction(
                                self.f.get_free_iid(),
                                use.bb,
                                cfg.Instruction.STORE,
                                intval.var)

                        instr_before[use.id].append(load)
                        instr_after[use.id].append(store)

            # rewrite instructions.
            for bb in self.bblocks.values():
                new_instructions = []
                for instr in bb.instructions:
                    for ib in instr_before[instr.id]:
                        new_instructions.append(ib)
                    new_instructions.append(instr)
                    for ia in instr_after[instr.id]:
                        new_instructions.append(ia)

                bb.set_instructions(new_instructions)
                
                # TODO: is liveness analysis dependent on SSA ?
                # because we need to redo it

            self.f.compute_devs_and_uevs()
            sefl.f.perform_liveness_analysis()



