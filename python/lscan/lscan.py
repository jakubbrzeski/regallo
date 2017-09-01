import utils

class LinearScan: 
    def __init__(self, f):
        self.f = f

        # This is dictionary of intervals. Each variable may have more then one interval,
        # e.g. after splitting or when we consider holes in the intervals or when we break
        # SSA form. That's why we keep a list of SubIntervals for each variable id.
        self.intervals = {}

        # We want to browse the basic blocks backwards.
        # Postorder guarantees that if a DOM> b, we will visit
        # b first. 
        self.bbs = utils.reverse_postorder(f)

        utils.number_instructions(self.bbs)

    def compute_intervals(self):
        raise NotImplementedError()

    def allocate_registers(self, intervals, regcount):
        raise NotImplementedError()

    # This function deals with spill code insertion, PHI Elimination or 
    # MOV insertion between split intervals. 
    def resolve(self, intervals):
        raise NotImplementedError()

    # Performs full register allocation from interval computation to
    # PHI destruction and resolution. At the end performs full analaysis
    # on the input function.
    def full_register_allocation(self, regcount):
        intervals = self.compute_intervals()
        self.allocate_registers(intervals, regcount)
        self.resolve(intervals)
        self.f.perform_full_analysis()

