from lscan import LinearScan
from intervals import AdvInterval, update

class AdvLinearScan(LinearScan):

    def compute_intervals(self):
        intervals = {v.id: AdvInterval(v) for v in self.f.vars.values()}

        for bb in self.bbs[::-1]:
            for v in bb.live_out:
                intervals[v.id].add_subinterval(bb.first_instr(), bb.last_instr())

            for instr in bb.instructions[::-1]:
                if instr.definition:
                    intervals[v.id].get_last_subinterval().fr = instr
                    update(iv, instr, instr)

                if not instr.is_phi():
                    for v in instr.uses:
                        iv = intervals[v.id]
                        iv.get_last_subinterval().to = instr
                        update(iv, instr, instr)
                        iv.uses.append(instr)

            if bb.is_loop_header():
                start = bb.loop.header.first_instr()
                end = bb.loop.header.last_instr()
                for v in bb.live_in:
                    update(intervals[v.id], start, end)
                    intervals[v.id].add_subinterval(start, end)

        for iv in intervals.values():
            iv.rebuild_and_order_subintervals()

        return {vid: [iv] for (vid, iv) in intervals.iteritems() if not iv.empty()}


    def allocate_registers(self, intervals, regcount):
        pass

    def resolve(self, intervals):
        pass
        
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

