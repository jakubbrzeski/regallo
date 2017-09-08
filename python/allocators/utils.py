import cfg.resolve as resolve

# Performs full register allocation on a given function using provided
# allocator with specific number of available registers. 
# First, it performs allocation with spilling TODO: finish.
def perform_full_register_allocation(f, allocator, regcount):    
    first_phase_regcount = regcount
    while (first_phase_regcount >= 0):
        allocator.full_allocation(f, first_phase_regcount)
        resolve.insert_spill_code(f)
        f.perform_full_analysis()

        success = allocator.full_allocation(f, regcount, spilling=False)
        if success:
            resolve.eliminate_phi(f, regcount)
            f.perform_full_analysis()
            return True

        first_phase_regcount -= 1

    return False
