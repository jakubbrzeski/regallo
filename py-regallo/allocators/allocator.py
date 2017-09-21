from cfg import Module
import cfg.resolve as resolve
import cfg.printer as printer
import cfg.analysis as analysis

class Allocator(object):
    def __init__(self, name):
        self.name = name

    # Performs one phase of register allocation for provided function
    # and number of available registers and returns True or False
    # if it was successfull or not. If might spill some variables
    # introducing new ones which need additional allocation.
    def perform_register_allocation(self, f, regcount, spilling=True):
        raise NotImplementedError()

    # Performs full register allocation on a given function
    # with specific number of available registers. In case of success it returns
    # the modified copy of the function and None otherwise.
    def perform_full_register_allocation(self, f, regcount):
        first_phase_regcount = regcount

        def try_allocate_and_eliminate_phi(fprim, rc, spilling):
            while rc >= 0:
                g = fprim.copy()
                allocation_success = self.perform_register_allocation(g, rc, spilling)
                if not allocation_success:
                    return (g, False)
                phi_elimination_success = resolve.eliminate_phi(g, regcount)
                if phi_elimination_success:
                    return (g, True)
                rc -= 1

            return None


        while first_phase_regcount >= 0:
            g, success = try_allocate_and_eliminate_phi(f, first_phase_regcount, spilling=True)
            if success:
                analysis.perform_full_analysis(g)
                return g

            resolve.insert_spill_code(g)
  
            h, success = try_allocate_and_eliminate_phi(g, regcount, spilling=False) 
            if success:
                analysis.perform_full_analysis(h)
                return h

            first_phase_regcount -= 1


        return None


    # Performs full register allocation on each function in a module with provided 
    # number of available registers. If register allocation succeeded for each
    # function from the module, a copy of the module with modified function copies is
    # returned. If allocation failed for at least one function, None is returned.
    def perform_full_module_register_allocation(self, m, regcount):
        processed_functions = []
        for f in m.functions.values():
            g = self.perform_full_register_allocation(f, regcount)
            if g is None:
                return None
            processed_functions.append(g)

        return Module(m.name, processed_functions)
