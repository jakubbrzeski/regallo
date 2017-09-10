from sortedcontainers import SortedSet
from allocators.lscan import LinearScan
from allocators.lscan.intervals import ExtendedInterval
from sys import maxint
import spillers
import utils

class ExtendedLinearScan(LinearScan):
    def __init__(self, spiller=spillers.default(), name="Extended Linear Scan"):
        super(ExtendedLinearScan, self).__init__(name)
        self.spiller = spiller

    def compute_intervals(self, f):
        intervals = {v.id: ExtendedInterval(v) for v in f.vars.values()}
        bbs = utils.reverse_postorder(f)
        utils.number_instructions(bbs)

        for bb in bbs[::-1]:
            for v in bb.live_out:
                intervals[v.id].add_subinterval(
                        bb.first_instr().num - 0.5, 
                        bb.last_instr().num + 0.5)

            for instr in bb.instructions[::-1]:
                if instr.definition:
                    intervals[instr.definition.id].defn = instr
                    last_sub = intervals[instr.definition.id].get_last_subinterval()
                    if last_sub: 
                        last_sub.fr = instr.num


                if instr.is_phi():
                    for (bid, v) in instr.uses.iteritems():
                        intervals[v.id].uses.append(instr)

                else:
                    for v in instr.uses:
                        intervals[v.id].uses.append(instr)
                        last_sub = intervals[v.id].get_last_subinterval()
                        if not last_sub or last_sub.fr > instr.num: 
                            intervals[v.id].add_subinterval(
                                    bb.first_instr().num - 0.5, 
                                    instr.num)


        for iv in intervals.values():
            if not iv.empty():
                iv.rebuild_and_order_subintervals()
                iv.update_endpoints(iv.subintervals[0].fr, iv.subintervals[-1].to)

        return {vid: [iv] for (vid, iv) in intervals.iteritems() if not iv.empty()}



    def try_allocate_free_register(self, current, active, inactive, regset):
        reg = regset.get_free()
        if reg:
            current.allocate(reg)
            active.add(current)
            return reg

        """
        According to Wimmer, Franz "Linear Scan Register Allocation on SSA Form":

        All intervals in inactive start before the current interval, so they do 
        not intersect with the current interval at their definition. 
        They are inactive and thus have a lifetime hole at the current position, 
        so they do not intersect with the current interval at its definition. 
        SSA form therefore guarantees that they never intersect.
        
        Unfortunately, splitting of intervals leads to intervals that no
        longer adhere to the SSA form properties because it destroys SSA
        form. Therefore, the intersection test cannot be omitted completely;
        it must be performed if the current interval has been split off from
        another interval.

         v1 |------           ----
         v2 |------  ----     ----
            ^        ^        ^
            phi      loop     after loop
        
        We have 3 basic blocks. v1 is live in the loop header and after the loop.
        v2 is live in header, some time in the loop body and after the loop.
        Let's assume we split v2 at the beginning of the loop body where v1 has
        lifetime hole. Becauce v2 has a new interval here, it doesn't start with
        definition, so we don't know if definitions of v1 and v2 overlap. That's
        why we can't be sure if the intervals intersect or not.
        """

        if not current.split and inactive:
            # TODO: poor complexity. Change that. E.g. remember and pass active_regs.
            occupied_regs = set([iv.alloc for iv in active])
            for iv in inactive:
                if iv.alloc not in occupied_regs:
                    current.allocate(iv.alloc)
                    active.add(current)
                    return iv.alloc

            return None

        elif current.split and inactive: 
            regs = {} # reg -> (min free_until_pos for all ivs with this reg, iv)
            for iv in inactive:
                cfup = iv.intersection(current.fr)
                if cfup is None:
                    cfup = maxint

                if iv.reg not in regs or cfup < regs[reg][0]:
                    regs[reg] = (cfup, iv)

            # Choose reg with max free_until_pos.
            m = None
            for reg, (fup, iv) in regs.iteritems():
                if m is None or m[0] < fup:
                    m = (fup, iv)
            
            # TODO: Split current until m[0]
            current.allocate(iv.alloc)
            active.add(current)
            return iv.alloc

        return None

    def allocate_registers(self, intervals, regcount, spilling=True):
        regset = utils.RegisterSet(regcount)

        class Action:
            START, END = 1, -1
            def __init__(self, num, kind, sub):
                self.num = num
                self.kind = kind
                self.sub = sub

        # Actions are sorted by instruction number and kind.
        actions = SortedSet(key = lambda action: (action.num, action.kind))

        for ivlist in intervals.values():
            for sub in ivlist[0].subintervals:
                actions.add(Action(sub.fr, Action.START, sub))
                actions.add(Action(sub.to, Action.END, sub))

        active  = SortedSet(key = lambda iv: iv.to)
        inactive = SortedSet(key = lambda iv: iv.to)

        for action in actions:
            sub, iv = action.sub, action.sub.parent
            #print " NUM:", action.num, "sub", iv.var.id, "kind: ", action.kind, "[", sub.fr, sub.to, "]", "alloc: ", iv.alloc

            if action.kind == Action.END and iv in active:
                #print "OPTION 1"
                # If it was not in active, it must have been spilled.
                active.remove(iv)
                if sub.to < iv.to: # If it's not the last subinterval.
                    inactive.add(action.sub.parent)

                regset.set_free(iv.alloc)

            elif action.kind == Action.START and iv.fr == sub.fr: 
                # If this SubInterval is the beginning of new Interval.
                #print "OPTION 2"
                reg_found = self.try_allocate_free_register(iv, active, inactive, regset)
                if not reg_found:
                    if spilling:
                        spilled = self.spiller.spill_at_interval(iv, active, inactive)
                        #print "Spilling: ", spilled.var.id, "[", spilled.fr, spilled.to, "]"
                    else:
                        return False

            elif action.kind == Action.START and iv in inactive: 
                #print "OPTION 3"
                # If it was not in inactive, it must have been spilled.
                inactive.remove(iv)
                active.add(iv)
                regset.occupy(iv.alloc)
            
            #print "active:", [(ivv.var.id, ivv.alloc) for ivv in active]
            #print "inactive:", [(ivv.var.id, ivv.alloc) for ivv in inactive]
            #print "occupied regs:", regset.occupied
            #print ""

        return True

    def resolve(self, intervals):
        # If there were no splits, we don't need resolving.
        pass
       
