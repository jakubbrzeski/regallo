class Spiller(object):
    def spill_at_interval(self, current, active, inactive):
        raise NotImplementedError()


class FurthestFirst(Spiller):
    def spill_at_interval(self, current, active, inactive):
        furthest = (0, None)
        for iv in list(active) + list(inactive):
            if furthest[0] < iv.to:
                furthest = (iv.to, iv)

        spilled = furthest[1]
        if spilled and spilled.to > current.to:
            reg = spilled.alloc
            for iv in list(active):
                if iv.alloc == reg:
                    active.remove(iv)

            for iv in list(inactive):
                if iv.alloc == reg:
                    inactive.remove(iv)

            current.allocate(reg)
            spilled.spill()
            active.add(current)
            return spilled

        else:
            current.spill()
            return current

class FurthestNextUseFirst(Spiller):
    def spill_at_interval(self, current, active, inactive):
        furthest = (0, None)
        for iv in list(active) + list(inactive):
            for use in iv.uses:
                if use.num > current.fr:
                    if furthest[0] < use.num:
                        furthest = (use.num, iv)
                    break

        if furthest[1] and furthest[0] > current.fr:
            spilled = furthest[1]
            reg = spilled.alloc
            
            for iv in list(active):
                if iv.alloc == reg:
                    active.remove(iv)

            for iv in list(inactive):
                if iv.alloc == reg:
                    inactive.remove(iv)
            
            current.allocate(reg)
            spilled.spill()
            active.add(current)
            return spilled

        else:
            current.spill()
            return current
       


def default():
    return FurthestFirst()
