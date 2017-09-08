class Allocator(object):
    def __init__(self, name):
        self.name = name

    # Performs one phase of register allocation for provided function
    # and number of available registers and returns True or False
    # if it was successfull or not. If might spill some variables
    # introducing new ones which need additional allocation.
    def perform_register_allocation(self, f, regcount, spilling=True):
        raise NotImplementedError()

