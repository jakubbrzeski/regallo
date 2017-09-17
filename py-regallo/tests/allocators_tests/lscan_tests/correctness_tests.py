import unittest
from allocators.lscan.basic import BasicLinearScan
import allocators.lscan.basic.spillers as basic_spillers
from allocators.lscan.extended import ExtendedLinearScan
import allocators.lscan.extended.spillers as exteded_spillers

import tests.cfgmocks as cfgmocks
import cfg
import cfg.sanity
import cfg.analysis as analysis


ALLOCATORS = [
    BasicLinearScan(),
    BasicLinearScan(spiller=basic_spillers.CurrentFirst(), name="current"),
    BasicLinearScan(spiller=basic_spillers.LessUsedFirst(), name="lessUsed"),
    ExtendedLinearScan()]
        

# Tries allocate registers in our test programs multiple times with
# different number of available registers, each time checking if the allocation
# is correct i.e. if at all program points every live variable has a register
# assigned and every two variables have different registers assigned
class CorrectnessTests(unittest.TestCase):
    def assert_correct(self, m, allocator, regcount):
        pass
   
    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_correct(m, allocator, 2)
            self.assert_correct(m, allocator, 3)
            self.assert_correct(m, allocator, 4)
            self.assert_correct(m, allocator, 5)
       
    def test_sort(self):
        m = cfg.Module.from_file("programs/sort.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_correct(m, allocator, 2)
            self.assert_correct(m, allocator, 3)
            self.assert_correct(m, allocator, 4)
            self.assert_correct(m, allocator, 5)

    def test_gjk(self):
        m = cfg.Module.from_file("programs/gjk.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_correct(m, allocator, 3)
            self.assert_correct(m, allocator, 5)
            self.assert_correct(m, allocator, 7)
            self.assert_correct(m, allocator, 8)

    def test_fft(self):
        m = cfg.Module.from_file("programs/fft.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_correct(m, allocator, 3)
            self.assert_correct(m, allocator, 5)
            self.assert_correct(m, allocator, 7)
            self.assert_correct(m, allocator, 8)

class AllocationCorrectnessTests(CorrectnessTests):
    def assert_correct(self, m, allocator, regcount):
        for f in m.functions.values():
            result = allocator.perform_full_register_allocation(f, regcount)
            if result:
                correct = cfg.sanity.allocation_is_correct(result)
                self.assertTrue(correct)

class DataFlowCorrectnessTests(CorrectnessTests):
    def assert_correct(self, m, allocator, regcount):
        for f in m.functions.values():
            result = allocator.perform_full_register_allocation(f, regcount)
            if result:
                correct = cfg.sanity.data_flow_is_correct(result, f)
                self.assertTrue(correct)


class AllocationWithMinRegPressureTests(unittest.TestCase):
    def assert_allocation_success(self, m, allocator):
        for f in m.functions.values():
            minimal_pressure = f.minimal_register_pressure()
            result = allocator.perform_full_register_allocation(f, minimal_pressure)
            self.assertIsNotNone(result)

            # It shouldn't pass with fewer registers
            result = allocator.perform_full_register_allocation(f, minimal_pressure-1)
            self.assertIsNone(result)

    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_allocation_success(m, allocator) 

    def test_sort(self):
        m = cfg.Module.from_file("programs/sort.json")
        analysis.perform_full_analysis(m)
        for allocator in ALLOCATORS:
            self.assert_allocation_success(m, allocator)

    def test_gjk(self):
        m = cfg.Module.from_file("programs/gjk.json")
        analysis.perform_full_analysis(m)
        self.assert_allocation_success(m, ALLOCATORS[0])
        for allocator in ALLOCATORS:
            self.assert_allocation_success(m, allocator)

