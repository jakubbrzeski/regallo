import unittest
import utils
from dashtable import data2rst
from copy import deepcopy

class ResultTableTests(unittest.TestCase):

    def test1(self):
        f1 = [(1, [("Allocator1", [("cost1",1), ("cost2",2), ("cost3",3)]),
                   ("Allocator2", [("cost1",1), ("cost2",2), ("cost3",3)])]),
              (2, [("Allocator1", [("cost1",1), ("cost2",2), ("cost3",3)]),
                   ("Allocator2", [("cost1",1), ("cost2",2), ("cost3",3)])]),
              (3, [("Allocator1", [("cost1",1), ("cost2",2), ("cost3",3)]),
                   ("Allocator2", [("cost1",1), ("cost2",2), ("cost3",3)])])]

        f2 = deepcopy(f1)
        f3 = deepcopy(f2)
        d = [("f1", f1), ("f2", f2), ("f3", f3)]
       
        class Setting:
            def allocator_names(self):
                return ["Allocator1", "Allocator2"]
            def cost_calc_names(self):
                return ["cost1", "cost2", "cost3"]
        setting = Setting()

        table, spans = utils.compute_result_table(d, setting)

        correct_table = [
            ['', '', 'Allocator1', '', '', 'Allocator2', '', ''],
            ['Functions', 'Registers', 'cost1', 'cost2', 'cost3', 'cost1', 'cost2', 'cost3'],
            ['f1', 1, 1, 2, 3, 1, 2, 3],
            ['', 2, 1, 2, 3, 1, 2, 3],
            ['', 3, 1, 2, 3, 1, 2, 3],
            ['f2', 1, 1, 2, 3, 1, 2, 3],
            ['', 2, 1, 2, 3, 1, 2, 3],
            ['', 3, 1, 2, 3, 1, 2, 3],
            ['f3', 1, 1, 2, 3, 1, 2, 3],
            ['', 2, 1, 2, 3, 1, 2, 3],
            ['', 3, 1, 2, 3, 1, 2, 3]]
        self.assertEqual(table, correct_table)

        correct_spans = [
                [[0, 0], [0, 1]],
                [[0, 2], [0, 3], [0, 4]], 
                [[0, 5], [0, 6], [0, 7]], 
                [[2, 0], [3, 0], [4, 0]], 
                [[5, 0], [6, 0], [7, 0]], 
                [[8, 0], [9, 0], [10, 0]]
                ]
        self.assertEqual(spans, correct_spans)

        #print(data2rst(table, spans=spans, use_headers=True))

    def test2(self):
        d = [("f1", [(1, [("Allocator1", [("cost1",1)]),
                          ("Allocator2", [("cost1",1)]) ]),
                     (2, [("Allocator1", [("cost1",1)]),
                          ("Allocator2", [("cost1",1)]) ]),
                     (3, [("Allocator1", [("cost1",1)]),
                          ("Allocator2", [("cost1",1)]) ]) ])]
        class Setting:
            def allocator_names(self):
                return ["Allocator1", "Allocator2"]
            def cost_calc_names(self):
                return ["cost1"]
        setting = Setting()

        table, spans = utils.compute_result_table(d, setting)

        correct_table = [
            ['', '', 'Allocator1', 'Allocator2'],
            ['Functions', 'Registers', 'cost1', 'cost1'],
            ['f1', 1, 1, 1],
            ['', 2, 1, 1],
            ['', 3, 1, 1]]
        self.assertEqual(table, correct_table)

        correct_spans = [
                [[0, 0], [0, 1]],
                [[2, 0], [3, 0], [4, 0]]]
        self.assertEqual(spans, correct_spans)
        #print(data2rst(table, spans=spans, use_headers=True))

    
    def test3(self):
        d = [("f1", [(1, [("Allocator1", [("cost1", 1)] )] )] )]

        class Setting:
            def allocator_names(self):
                return ["Allocator1"]
            def cost_calc_names(self):
                return ["cost1"]
        setting = Setting()

        table, spans = utils.compute_result_table(d, setting)

        correct_table = [
            ['', '', 'Allocator1'],
            ['Functions', 'Registers', 'cost1'],
            ['f1', 1, 1]]
        self.assertEqual(table, correct_table)

        correct_spans = [[[0, 0], [0, 1]]]
        self.assertEqual(spans, correct_spans)
        #print(data2rst(table, spans=spans, use_headers=True))


if __name__ == '__main__':
    unittest.main()
