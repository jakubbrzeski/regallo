class Spiller(object):
    def spill_at_interval(self, current, active, inactive):
        raise NotImplementedError()


class FurthestFirst(Spiller):
    def spill_at_interval(self, current, active, inactive):
        spill_source = None # Active or inactive.

        if active and inactive:
            spill_source = active if active[-1].to > inactive[-1].to else inactive
        elif active:
            spill_source = active
        elif inactive:
            spill_source = inactive
        else:
            current.spill()
            return current

        spilled = spill_source[-1] 
        if spilled.to > current.to:
            current.allocate(spilled.alloc)
            spilled.spill()
            spill_source.remove(spilled)
            spill_source.add(current)
            return spilled

        else:
            current.spill()
            return current


class FurthestNextUsePosFirst(Spiller):
    def spill_at_interval(self, current, active, inactive):
        # Inactive should be empty here.
        if not active:
            current.spill()
            return

        # All intervals in active are live at the current position, so
        # all of them must have different registers.
        # We will choose an interval with the furthest next use position.
        m = None # (max next use position, interval)
        for iv in active:
            nup = iv.next_use(current.fr).num
            if m is None or m[0] < nup:
                m = (nup, iv)

        cnup = current.next_use(current.fr).num
        if cnup < m[0]:
            iv = m[1]
            current.allocater(iv.alloc)
            # TODO: Split iv before its next use pos.
            iv.spill()
            active.remove(iv)
            active.add(current)

        else:
            # TODO: Split current before cnup ?
            current.spill()
            

def default():
    return FurthestFirst()
