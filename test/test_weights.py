from cherrycommon.mathutils import Weights
import unittest


class WeightsTest(unittest.TestCase):
    ITERATIONS = 100000

    def test_tough(self):
        values = {'a': 0, 'b': 0, 'c': 0}
        weights = Weights(a=1, b=1, c=5)
        delta = self.ITERATIONS * 0.05

        for i in range(0, self.ITERATIONS):
            values[weights.choice()] += 1
        self.assertAlmostEqual(values['a'], values['b'], delta=delta)
        self.assertAlmostEqual(values['a'] * 5, values['c'], delta=delta)

        # Weights update
        values = {'a': 0, 'b': 0, 'c': 0, 'd': 0}
        weights['a'] = 2
        weights['d'] = 5
        for i in range(0, self.ITERATIONS):
            values[weights.choice()] += 1
        self.assertAlmostEqual(values['a'], values['b'] * 2, delta=delta)
        self.assertAlmostEqual(values['c'], values['d'], delta=delta)

    def test_reverse(self):
        values = {'a': 0, 'b': 0, 'c': 0, 'd': 0}
        weights = Weights(a=1, b=1, c=5, d=5)
        delta = self.ITERATIONS * 0.05

        for i in range(0, self.ITERATIONS):
            values[weights.choice()] += 1

        weights.update(values)
        for i in range(0, self.ITERATIONS * (len(weights) - 1)):
            values[weights.choice(True)] += 1

        print values
        self.assertAlmostEqual(values['a'], values['b'], delta=delta)
        self.assertAlmostEqual(values['a'], values['c'], delta=delta)
        self.assertAlmostEqual(values['a'], values['d'], delta=delta)


if __name__ == '__main__':
    unittest.main()
