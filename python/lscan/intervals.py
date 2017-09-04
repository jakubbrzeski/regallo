import utils

class Interval(object):
    def __init__(self, var, fr=None, to=None, alloc=None, defn=None, uses=None):
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
        return self.fr == self.to
    
    def update(self, fr, to):
        if self.fr is None or self.fr.num > fr.num:
            self.fr = fr
        if self.to is None or self.to.num < to.num:
            self.to = to

    def update_variables(self, alloc):
        if self.defn is not None:
            self.var.alloc[self.defn.id] = alloc
        for use in self.uses:
            self.var.alloc[use.id] = alloc

    def allocate(self, alloc):
        self.alloc = alloc
        self.update_variables(alloc)

    def spill(self):
        self.alloc = utils.slot(self.var)
        self.update_variables(self.alloc)


class AdvInterval(Interval):
    class SubInterval:
        def __init__(self, fr, to, parent):
            self.fr = fr # Instruction it starts with.
            self.to = to # Instruction it ends with.
            self.parent = parent # Parent AdvInterval.

    def __init__(self, var, fr=None, to=None, alloc=None, defn=None, uses=None):
        super(AdvInterval, self).__init__(var, fr, to, alloc, defn, uses)
        # Stack (list) of subintervals.
        self.subintervals = []

    def add_subinterval(self, fr, to):
        siv = AdvInterval.SubInterval(fr, to, self)
        self.subintervals.append(siv)
        return siv

    def empty(self):
        return len(self.subintervals) == 0

    def get_last_subinterval(self):
        if self.empty():
            return None
        return self.subintervals[-1]

    # During intervals computation, we add new subintervals loosely,
    # no matter whether some of them overlap or not. This function
    # reorder and stick together 
    def rebuild_and_order_subintervals(self):
        if not self.subintervals:
            return
        new = []
        subs = sorted(self.subintervals, key = lambda sub: sub.fr.num)
        start, end = subs[0].fr, subs[0].to
        for sub in subs[1:]:
            if sub.fr.num > end.num + 1:
                new.append(AdvInterval.SubInterval(start, end, self))
                start, end = sub.fr, sub.to
            elif sub.to.num > end.num:
                end = sub.to
        new.append(AdvInterval.SubInterval(start, end, self))
        self.subintervals = new
        
