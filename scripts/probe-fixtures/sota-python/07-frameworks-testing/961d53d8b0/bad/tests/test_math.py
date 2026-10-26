import unittest


class MathTest(unittest.TestCase):
    def setUp(self):
        self.x = 2

    def test_double(self):
        self.assertEqual(double(self.x), 4)
