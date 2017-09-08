class Spiller(object):
    def spill_at_interval(self, current, active, inactive):
        raise NotImplementedError()


class FurthestNextUsePos(Spiller):
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
    return FurthestNextUsePos()
