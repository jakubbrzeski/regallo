import utils

class Interval(object):
    def __init__(self, var, fr=-0.5, to=0, alloc=None, defn=None, uses=None):
        # Variable this interval represents
        self.var = var
        # Instructions this interval starts and ends with.
        self.fr = fr
        self.to = to
        # Allocated register or memory slot.
        self.alloc = alloc
        # Note that it doesn't always need to be the same as self.fr.
        self.defn = defn
        # List of instructions which use self.var in this interval.
        self.uses = [] if uses is None else uses

    def empty(self):
        return not self.uses
    
    def update_endpoints(self, fr=None, to=None):
        if fr is not None and (self.fr is None or self.fr > fr):
            self.fr = fr
        if to is not None and (self.to is None or self.to < to):
            self.to = to

    def update_variables(self, alloc):
        if self.defn is not None:
            self.var.alloc = alloc
        for use in self.uses:
            self.var.alloc = alloc

    def allocate(self, alloc):
        self.alloc = alloc
        self.update_variables(alloc)

    def spill(self):
        self.alloc = utils.slot(self.var)
        self.update_variables(self.alloc)



# Extended version of the Interval used in ExtendedLinearScan
# register allocator. 
class ExtendedInterval(Interval):
    class SubInterval:
        def __init__(self, fr, to, parent):
            self.fr = fr
            self.to = to
            self.parent = parent # Parent ExtendedInterval.

        def is_last(self):
            return self.index == len(self.parent.subintervals) - 1

        def intersection(self, another):
            if another.fr >= self.fr and another.fr<= self.to:
                return another.fr
            if self.fr >= another.fr and self.fr <= another.to:
                return self.fr
            return None

    def __init__(self, var, fr=None, to=None, alloc=None, defn=None, uses=None):
        super(ExtendedInterval, self).__init__(var, fr, to, alloc, defn, uses)
        self.subintervals = []
        self.split = False
        self.next_use = 0 if uses else None

    # For a single case O(n) but overall O(1).
    def next_use(self, num):
        if not self.uses or self.next_use >= len(self.uses):
            return None

        while (self.next_use < len(self.uses) and self.uses[self.next_use].num <= num):
            self.next_use += 1

        return self.next_use

    def add_subinterval(self, fr, to):
        siv = ExtendedInterval.SubInterval(fr, to, self)
        self.subintervals.append(siv)
        return siv

    def empty(self):
        return len(self.subintervals) == 0

    def get_last_subinterval(self):
        if self.empty():
            return None
        return self.subintervals[-1]

    # O(m lg m), where m = len(self.subintervals) + len(another.subintervals)
    def intersection(self, another):
        sorted_subs = sorted(self.subintervals + another.subintervals,
                key = lambda sub: (sub.fr, sub.to))

        # If two subsequent subintervals intersect, it means they are
        # from different intervals. If i-th doesn't intersect with i+1-th
        # it also doesn't intersect with any further.
        for s1, s2 in zip(sorted_subs[:-1], sorted_subs[1:]):
            i = s1.intersection(s2)
            if i:
                return i
        
        return None

    # During intervals computation, we add new subintervals loosely,
    # no matter whether some of them overlap or not. This function
    # reorders and rebuild subintervals so that they won't overlap
    # and will be in increasing order.
    def rebuild_and_order_subintervals(self):
        if not self.subintervals:
            return
        new = []
        subs = sorted(self.subintervals, key = lambda sub: sub.fr)
        start, end = subs[0].fr, subs[0].to
        for sub in subs[1:]:
            if sub.fr > end + 1:
                new.append(ExtendedInterval.SubInterval(start, end, self))
                start, end = sub.fr, sub.to
            elif sub.to > end:
                end = sub.to
        new.append(ExtendedInterval.SubInterval(start, end, self))
        self.subintervals = new
      
    # Splits this interval into two intervals: self = [fr, pos-1] and new = [pos, to]
    # Returns the new interval.
    def split_at(self, pos):
        # subintervals
        sub_old = [] # Subintervals staying in first interval (self).
        sub_new = [] # Subintervals going to sub_new interval.
        for sub in self.subintervals:
            if sub.to < pos:
                sub_old.append((sub.fr, sub.to))
            elif sub.fr > pos:
                sub_new.append((sub.fr, sub.to))
            else:
                if pos > sub.fr:
                    sub_old.append((sub.fr, pos-1))
                sub_new.append((pos, sub.to))

        # endpoints
        fr_old, to_old = sub_old[0][0], sub_old[-1][1]
        self.fr = fr_old
        self.to = to_old

        fr_new, to_new = sub_new[0][0], sub_new[-1][1]

        # defn
        defn = None
        if self.defn.num >= fr_new:
            defn = self.defn
            self.defn = None

        # uses
        uses_old = []
        uses_new = []
        for instr in self.uses:
            num = instr.num
            # Variable used in phi instruction is live until the end
            # of corresponding predecessor block.
            if instr.is_phi():
                num = instr.phi_preds[self.var.id].last_instr().num

            if num < fr_new:
                uses_old.append(instr)
            else:
                uses_new.append(instr)
        self.uses = uses_old

        # Rewrite subintervals.
        self.subintervals = []
        for sub in sub_old:
            self.add_subinterval(sub[0], sub[1])

        # TODO: the same alloc or None?
        new_iv = ExtendedInterval(self.var, fr_new, to_new, self.alloc, defn, uses_new)
        for sub in sub_new:
            new_iv.add_subinterval(sub[0], sub[1])



        return new_iv

