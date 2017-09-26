class Spiller(object):
    # Chooses and spills one interval (may be current).
    # Returns the spilled interval.
    # 
    # active - SortedSet of intervals ordered by right endpoint.
    def spill_at_interval(self, current, active):
        raise NotImplementedError()


class FurthestFirst(Spiller):
    def spill_at_interval(self, current, active):
        if active:
            spilled = active[-1] # Active interval with furthest endpoint.
            if spilled.to > current.to:
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
                return spilled

        current.spill()
        return current

class FurthestNextUseFirst(Spiller):
    def spill_at_interval(self, current, active):
        if active:
            furthest = (0, None) # (Instr num, Interval)
            for iv in active:
                # Find first use after the current point.
                for use in iv.uses:
                    if use.num > current.fr:
                        if furthest[0] < use.num:
                            furthest = (use.num, iv)
                        break

            if furthest[0] > current.uses[0].num:
                spilled = furthest[1]
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
                return spilled

        current.spill()
        return current

class CurrentFirst(Spiller):
    def spill_at_interval(self, current, active):
        current.spill()
        return current


class LessUsedFirst(Spiller):
    def spill_at_interval(self, current, active):
        if active:
            spilled = current
            for iv in active:
                if len(iv.uses) < len(spilled.uses):
                    spilled = iv

            if spilled is not current:
                current.allocate(spilled.alloc)
                spilled.spill()
                active.remove(spilled)
                active.add(current)
                return spilled
        
        current.spill()
        return current


def default():
    return FurthestFirst()
