from allocators.lscan import LinearScan
from allocators.lscan.intervals import ExtendedInterval
from sys import maxint
import spillers
import utils

class ExtendedLinearScan(LinearScan):
    def __init__(self, spiller=spillers.default(), name="Basic Linear Scan"):
        super(ExtendedLinearScan, self).__init__(name)
        self.spiller = spiller

    def compute_intervals(self, f):
        intervals = {v.id: ExtendedInterval(v) for v in f.vars.values()}
        bbs = utils.reverse_postorder(f)
        utils.number_instructions(bbs)

        for bb in bbs[::-1]:
            for v in bb.live_out:
                intervals[v.id].add_subinterval(bb.first_instr(), bb.last_instr())

            for instr in bb.instructions[::-1]:
                if instr.definition:
                    iv = intervals[instr.definition.id]
                    iv.defn = instr
                    if iv.uses: # If this variable is ever used.
                        iv.get_last_subinterval().fr = instr.num
                    iv.update_endpoints(instr, instr)

                if instr.is_phi():
                    for (bid, v) in instr.uses.iteritems():
                        iv = intervals[v.id]
                        pred = f.bblocks[bid]
                        iv.update_endpoints(pred.last_instr(), pred.last_instr())
                        iv.uses.append(instr)

                else:
                    for v in instr.uses:
                        iv = intervals[v.id]
                        iv.add_subinterval(bb.first_instr(), instr)
                        iv.update_endpoints(instr, instr)
                        iv.uses.append(instr)

        for iv in intervals.values():
            iv.rebuild_and_order_subintervals()

        return {vid: [iv] for (vid, iv) in intervals.iteritems() if not iv.empty()}



    def try_allocate_free_register(self, current, active, inactive, regset):
        reg = regset.get_free()
        if reg:
            current.allocate(reg)
            active.add(current)
            return True

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
            iv = inactive.pop()
            current.allocate(iv.reg)
            active.add(current)
            return True

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
            current.allocate(iv.reg)
            active.add(current)
            return True

        return False

    def allocate_registers(self, intervals, regcount, spilling=True):
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
           
            if action.kind == Action.END:
                active.remove(iv)
                if not sub.is_last():
                    inactive.add(action.sub.parent)

            elif iv.fr == sub.fr: # If this SubInterval is the beginning of new Interval.
                reg_found = self.try_allocate_free_register(iv, active, inactive, regset):
                if not reg_found and spilling:
                    self.spiller.spill_at_interval(iv, active, inactive)
                else:
                    return False

            else:
                inactive.remove(iv)
                active.add(iv)

        return True

    def resolve(self, intervals):
        pass
       
