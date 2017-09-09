import cfg.resolve as resolve

class Allocator(object):
    def __init__(self, name):
        self.name = name

    # Performs one phase of register allocation for provided function
    # and number of available registers and returns True or False
    # if it was successfull or not. If might spill some variables
    # introducing new ones which need additional allocation.
    def perform_register_allocation(self, f, regcount, spilling=True):
        raise NotImplementedError()


    # Performs full register allocation on a given function using provided
    # allocator with specific number of available registers. 
    # First, it performs allocation with spilling TODO: finish.
    def perform_full_register_allocation(self, f, regcount):
        first_phase_regcount = regcount
        while (first_phase_regcount >= 0):
            self.perform_register_allocation(f, first_phase_regcount, spilling=True)
            resolve.insert_spill_code(f)
            f.perform_full_analysis()

            success = self.perform_register_allocation(f, regcount, spilling=False)
            if success:
                resolve.eliminate_phi(f, regcount)
                f.perform_full_analysis()
                return True

            first_phase_regcount -= 1

        return False


