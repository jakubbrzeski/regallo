class Spiller(object):
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
                return

        current.spill()


class CurrentFirst(Spiller):
    def spill_at_interval(self, current, active):
        current.spill()


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
                return
        
        current.spill()


def default():
    return FurthestFirst()
