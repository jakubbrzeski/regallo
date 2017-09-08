import unittest
from allocators.lscan.intervals import ExtendedInterval

SubInterval = ExtendedInterval.SubInterval

class ExtendedIntervalsTest(unittest.TestCase):

    def test_intersection(self):
        iv1 = ExtendedInterval("v1")
        iv2 = ExtendedInterval("v2")
        
        sub1 = SubInterval(1, 4, None)
        sub2 = SubInterval(5, 7, None)
        self.assertIsNone(sub1.intersection(sub2))

        sub1 = SubInterval(1, 5, None)
        sub2 = SubInterval(4, 7, None)
        self.assertEqual(sub1.intersection(sub2), 4)

        # iv1 = [[1, 4], [11, 14], [17, 18]]
        # iv2 = [[5, 7], [8, 10], [13, 16], [17, 19]]
        # correct answer = 13

        iv1.add_subinterval(1, 4)
        iv1.add_subinterval(11, 14)
        iv1.add_subinterval(17, 18)

        iv2.add_subinterval(5, 7)
        iv2.add_subinterval(8, 10)
        iv2.add_subinterval(13, 16)
        iv2.add_subinterval(17, 19)

        self.assertEqual(iv1.intersection(iv2), 13)

    def test_subintervals(self):
        iv = ExtendedInterval(None)

        Sub = ExtendedInterval.SubInterval

        subA = Sub(1, 2, iv)
        subB = Sub(3, 6, iv)
        subC = Sub(3, 13, iv)
        subD = Sub(8, 11, iv)
        subE = Sub(12, 15, iv)
        subF = Sub(17, 19, iv)
        subG = Sub(17, 19, iv)

        iv.subintervals = [subA, subB, subC, subD, subE, subF, subG]

        iv.rebuild_and_order_subintervals()

        def sub_equal(sub1, sub2):
            return sub1.fr == sub2.fr and sub1.to == sub2.to

        self.assertEqual(len(iv.subintervals), 2)
        self.assertTrue(sub_equal(iv.subintervals[0], Sub(1, 15, iv)))
        self.assertTrue(sub_equal(iv.subintervals[1], subF))

