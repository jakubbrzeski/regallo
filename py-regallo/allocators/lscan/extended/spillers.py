class Spiller(object):
    def spill_at_interval(self, current, active, inactive):
        raise NotImplementedError()


class FurthestFirst(Spiller):
    def spill_at_interval(self, current, active, inactive):
        spill_source = None # Active or inactive.

        # If there are inactive intervals and we didn't find
        # a free registers, it means that there are other, small intervals
        # in 'active' set that fill their hole and occupy their registers.

        furthest = (None, None)
        for iv in active:
            if furthest[0] is None or furthest[0].to < iv.to:
                furthest = (iv, iv.alloc)

        for iv in inactive:
            if furthest[0] is None or furthest[0].to < iv.to:
                furthest = (iv, iv.alloc)

        spilled = furthest[0]
        if spilled and spilled.to > current.to:
            reg = furthest[1]
            to_remove = None
            for iv in active:
                if iv.alloc == reg:
                    to_remove = iv
            if to_remove:
                active.remove(to_remove)

            to_remove = None
            for iv in inactive:
                if iv.alloc == reg:
                    to_remove = iv
            if to_remove:
                inactive.remove(to_remove)

            current.allocate(reg)
            spilled.spill()
            active.add(current)
            return spilled

        else:
            
            current.spill()
            return current


def default():
    return FurthestFirst()
