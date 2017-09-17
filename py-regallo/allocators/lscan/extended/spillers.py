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


def default():
    return FurthestFirst()
