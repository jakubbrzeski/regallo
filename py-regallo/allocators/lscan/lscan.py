import utils
from allocators.allocator import Allocator

class LinearScan(Allocator): 
    def __init__(self, name):
        self.name = name

    # Computes and returns intervals out of the given function.
    def compute_intervals(self, f):
        raise NotImplementedError()

    # Modifies the function intervals were build from.
    def allocate_registers(self, intervals, regcount, spilling=True):
        raise NotImplementedError()

    # This function should deal with any function modification needed
    # after single phase of register allocation. E.g. mov insertion
    # between split intervals (if splitting is implemented).
    def resolve(self, intervals):
        raise NotImplementedError()

    # Performs full register allocation from interval computation to
    # PHI destruction and resolution. At the end performs full analaysis
    # on the input function.
    def perform_register_allocation(self, f, regcount, spilling=True):
        intervals = self.compute_intervals(f)
        success = self.allocate_registers(intervals, regcount, spilling)
        if success:
            self.resolve(intervals)
            return True

        return False

