import unittest
from basic import BasicLinearScan
import sys
sys.path.append('..')
import cfg
import cfgmocks

class AdvLinearScanTest(cfgmocks.GCDTest):

    def test_subintervals(self):
        iv = lscan.AdvInterval(None)
        class InstrMock:
            def __init__(self, num):
                self.num = num

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
        
        Sub = lscan.AdvInterval.SubInterval

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

        self.assertEqual(len(iv.subintervals), 3)
        self.assertTrue(sub_equal(iv.subintervals[0], subA))
        self.assertTrue(sub_equal(iv.subintervals[1], Sub(i3, i15, iv)))
        self.assertTrue(sub_equal(iv.subintervals[2], subF))
