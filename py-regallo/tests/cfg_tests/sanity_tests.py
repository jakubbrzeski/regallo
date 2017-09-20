import unittest
import cfg.sanity as sanity
import cfg

class ChordalityTests(unittest.TestCase):

    def test_not_chordal(self):


        var = [cfg.Variable("v"+str(i)) for i in range(0, 10)]

        # Tree
        neighs = {
                var[0]: [var[1], var[2]],
                var[1]: [var[3], var[4]],
                var[2]: [var[5], var[6]],
                var[3]: [var[1]],
                var[4]: [var[1]],
                var[5]: [var[2]],
                var[6]: [var[2]]}

        self.assertFalse(sanity.is_chordal(neighs))

        # 4-Cycle
        neighs = {
                var[0]: [var[3], var[1]],
                var[1]: [var[0], var[2]],
                var[2]: [var[1], var[3]],
                var[3]: [var[2], var[0]]}

        self.assertFalse(sanity.is_chordal(neighs))



    def test_chordal(self):

        var = [cfg.Variable("v"+str(i)) for i in range(0, 10)]

        # .---. (An edge)
        neighs = {
                var[0]: [var[1]],
                var[1]: [var[0]]}
        self.assertTrue(sanity.is_chordal(neighs))

        #   /\
        #  /  \
        #  ----
        #  | /|
        #  |/ |
        #  ----
        neighs = {
                var[0]: [var[1], var[2], var[3]],
                var[1]: [var[0], var[3]],
                var[2]: [var[0], var[3], var[4]],
                var[3]: [var[0], var[1], var[2], var[4]],
                var[4]: [var[2], var[3]]}

        self.assertTrue(sanity.is_chordal(neighs))




