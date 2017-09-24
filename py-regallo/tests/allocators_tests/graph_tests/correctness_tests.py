import unittest
import cfg
import cfg.sanity as sanity
import cfg.analysis as analysis
import allocators.graph as graph

class InterferenceGraphTests(unittest.TestCase):

    def assert_chordal(self, f):
        neighs = graph.build_interference_graph(f)
        self.assertTrue(sanity.is_chordal(neighs))
    
    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_chordal(f)

    def test_sort(self):
        m = cfg.Module.from_file("programs/sort.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_chordal(f)

    
    def test_gjk(self):
        m = cfg.Module.from_file("programs/gjk.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_chordal(f)

    
    def test_fft(self):
        m = cfg.Module.from_file("programs/fft.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_chordal(f)

    def test_factor(self):
        m = cfg.Module.from_file("programs/factor.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_chordal(f)

    
class BasicGraphColoringAllocatorTests(unittest.TestCase):

    def assert_allocation_success(self, f, regcount):
        bgca = graph.BasicGraphColoringAllocator()
        g = bgca.perform_full_register_allocation(f, regcount)
        self.assertIsNotNone(g)
        sanity.allocation_is_correct(g)
        sanity.data_flow_is_correct(g, f)
        

    def test_gcd(self):
        m = cfg.Module.from_file("programs/gcd.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_allocation_success(f, f.maximal_register_pressure())
            self.assert_allocation_success(f, f.minimal_register_pressure())

    def test_sort(self):
        m = cfg.Module.from_file("programs/sort.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_allocation_success(f, f.maximal_register_pressure())
            self.assert_allocation_success(f, f.minimal_register_pressure())

    def test_gjk(self):
        m = cfg.Module.from_file("programs/gjk.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_allocation_success(f, f.maximal_register_pressure())
            self.assert_allocation_success(f, f.minimal_register_pressure())

    def test_fft(self):
        m = cfg.Module.from_file("programs/fft.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_allocation_success(f, f.maximal_register_pressure())
            self.assert_allocation_success(f, f.minimal_register_pressure()+1)

    def test_factor(self):
        m = cfg.Module.from_file("programs/factor.json")
        analysis.perform_full_analysis(m)
        for f in m.functions.values():
            self.assert_allocation_success(f, f.maximal_register_pressure())
            self.assert_allocation_success(f, f.minimal_register_pressure())
