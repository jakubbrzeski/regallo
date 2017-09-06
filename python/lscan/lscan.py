import utils

class LinearScan(object): 
    def __init__(self):
        pass

    # Computes and returns intervals out of the given function.
    def compute_intervals(self, f):
        raise NotImplementedError()

    # Modifies the function intervals were build from.
    def allocate_registers(self, intervals, regcount):
        raise NotImplementedError()

    # This function deals with spill code insertion, PHI Elimination or 
    # MOV insertion between split intervals. 
    def resolve(self, intervals):
        raise NotImplementedError()

    # Performs full register allocation from interval computation to
    # PHI destruction and resolution. At the end performs full analaysis
    # on the input function.
    def full_register_allocation(self, f, regcount):
        intervals = self.compute_intervals(f)
        self.allocate_registers(intervals, regcount)
        #self.resolve(intervals)
        #self.f.perform_full_analysis()

