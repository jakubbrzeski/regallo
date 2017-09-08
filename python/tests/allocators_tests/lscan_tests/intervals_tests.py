import unittest
from allocators.lscan.intervals import AdvInterval

SubInterval = AdvInterval.SubInterval

class InstrMock:
    def __init__(self, num):
        self.num = num

class AdvIntervalsTest(unittest.TestCase):

    def test_intersection(self):
        iv1 = AdvInterval("v1")
        iv2 = AdvInterval("v2")
        
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

    def test_subintervals(self):
        iv = AdvInterval(None)

        i1 = InstrMock(1)
        i2 = InstrMock(2)
        i3 = InstrMock(3)
        i6 = InstrMock(6)
        i8 = InstrMock(8)
        i11 = InstrMock(11)
        i12 = InstrMock(12)
        i13 = InstrMock(13)
        i15 = InstrMock(15)
        i17 = InstrMock(17)
        i19 = InstrMock(19)
        
        Sub = AdvInterval.SubInterval

        subA = Sub(i1, i2, iv)
        subB = Sub(i3, i6, iv)
        subC = Sub(i3, i13, iv)
        subD = Sub(i8, i11, iv)
        subE = Sub(i12, i15, iv)
        subF = Sub(i17, i19, iv)
        subG = Sub(i17, i19, iv)

        iv.subintervals = [subA, subB, subC, subD, subE, subF, subG]

        iv.rebuild_and_order_subintervals()

        def sub_equal(sub1, sub2):
            return sub1.fr.num == sub2.fr.num and sub1.to.num == sub2.to.num

        self.assertEqual(len(iv.subintervals), 2)
        self.assertTrue(sub_equal(iv.subintervals[0], Sub(i1, i15, iv)))
        self.assertTrue(sub_equal(iv.subintervals[1], subF))

