import unittest
from lscan.intervals import AdvInterval

SubInterval = AdvInterval.SubInterval

class AdvIntervalsTest(unittest.TestCase):

    def test_intersection(self):
        iv1 = AdvInterval("v1")
        iv2 = AdvInterval("v2")
        
        class InstrMock:
            def __init__(self, num):
                self.num = num

        ins = [InstrMock(i) for i in range(20)]

        sub1 = SubInterval(ins[1], ins[4], None)
        sub2 = SubInterval(ins[5], ins[7], None)
        self.assertIsNone(sub1.intersection(sub2))

        sub1 = SubInterval(ins[1], ins[5], None)
        sub2 = SubInterval(ins[4], ins[7], None)
        self.assertEqual(sub1.intersection(sub2), 4)

        # iv1 = [[1, 4], [11, 14], [17, 18]]
        # iv2 = [[5, 7], [8, 10], [13, 16], [17, 19]]
        # correct answer = 13

        iv1.add_subinterval(ins[1], ins[4])
        iv1.add_subinterval(ins[11], ins[14])
        iv1.add_subinterval(ins[17], ins[18])

        iv2.add_subinterval(ins[5], ins[7])
        iv2.add_subinterval(ins[8], ins[10])
        iv2.add_subinterval(ins[13], ins[16])
        iv2.add_subinterval(ins[17], ins[19])

        self.assertEqual(iv1.intersection(iv2), 13)
