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

    

