import cfg.resolve as resolve
import cfg.printer as printer

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
    def perform_full_register_allocation(self, f, regcount):
        first_phase_regcount = regcount
        while (first_phase_regcount >= 0):
            # Phase 1: we allow spilling.
            g = f.copy()
            success = self.perform_register_allocation(g, first_phase_regcount, spilling=True)
            if success:
                # It succeeded without spilling.
                return g

            resolve.insert_spill_code(g)
            g.perform_full_analysis()
            
            # Phase 2: spilling forbidden.
            second_phase_regcount = regcount
            while (second_phase_regcount >= 1):
                h = g.copy()
                success = self.perform_register_allocation(h, regcount, spilling=False)
                if not success:
                    # Retry phase 1 with fewer registers.
                    break

                # Phi elimination.
                success = resolve.eliminate_phi(h, regcount)
                if success:
                    h.perform_full_analysis()
                    return h
            
                second_phase_regcount -= 1

            first_phase_regcount -= 1

        return None


