from copy import copy
from cherrycommon.dictutils import Diffed, DictView, ListView, dump_value

__author__ = 'sunrize'

import unittest

class DiffedCase(unittest.TestCase):
    def test_simple_get(self):
        diffed = Diffed({
            'flat_field': 1,
            'none_field': None,
            'list_field': [1, 2, 3],
            'dict_field': {
                'nested_flat': 1,
                'nested_dict': {
                    'field_1': 1,
                    'field_2': 1
                }
            }
        })

        self.assertRaises(KeyError, diffed.__getitem__, 'none_field')
        self.assertIsInstance(diffed['list_field'], ListView)
        self.assertIsInstance(diffed['dict_field'], Diffed)

    def test_diffed_get(self):
        diffed = Diffed({
            'flat_field': 1,
            'none_field': None
        })
        first_diff = {
            'flat_field': 2,
            'none_field': 2,
            'diffed_field': 2
        }
        diffed.add_diff(first_diff)

        self.assertEqual(diffed['flat_field'], first_diff['flat_field'])
        self.assertEqual(diffed['none_field'], first_diff['none_field'])
        self.assertEqual(diffed['diffed_field'], first_diff['diffed_field'])

        second_diff = {
            'flat_field': None,
            'none_field': 3,
        }
        diffed.add_diff(second_diff)
        self.assertRaises(KeyError, diffed.__getitem__, 'flat_field')
        self.assertEqual(diffed['none_field'], second_diff['none_field'])
        self.assertEqual(diffed['diffed_field'], first_diff['diffed_field'])

    def test_nested_get(self):
        diffed = Diffed({
            'nested': {
                'flat_field': 1,
                'none_field': None,
                'deleted_field': 1
            }
        })
        first_diff = {
            'nested': {
                'flat_field': 2,
                'none_field': 2,
                'deleted_field': None
            }
        }
        diffed.add_diff(first_diff)
        nested = diffed['nested']
        self.assertIsInstance(nested, Diffed)
        self.assertIn(first_diff['nested'], nested.diffs)
        self.assertEqual(nested['flat_field'], 2)
        self.assertEqual(nested['none_field'], 2)
        self.assertRaises(KeyError, nested.__getitem__, 'deleted_field')

        second_diff = {
            'nested': {
                'none_field': None,
                'deleted_field': 3
            },
        }
        diffed.add_diff(second_diff)
        nested = diffed['nested']

        self.assertIsInstance(nested, Diffed)
        self.assertEqual(list(nested.diffs), [first_diff['nested'], second_diff['nested']])
        self.assertRaises(KeyError, nested.__getitem__, 'none_field')
        self.assertEqual(nested['deleted_field'], 3)

    def test_add_diff(self):
        diffed = Diffed()
        diff = {}
        diffed.add_diff(diff)
        diff = DictView()
        diffed.add_diff(diff)
        diff = Diffed()
        self.assertRaises(TypeError, diffed.add_diff, diff)

    def test_complex_nested(self):
        diffed = Diffed({
            'nested': {
                'flat': 1
            },
            'another_nested': {
                'flat': 1
            }
        })
        first_diff = {
            'nested': None,
        }
        diffed.add_diff(first_diff)
        another_nested = diffed['another_nested']
        self.assertEqual(another_nested['flat'], 1)
        self.assertIn('another_nested', first_diff)

    def test_assign(self):
        data = {
            'flat': 1
        }
        diff = {
            'string': 'Some string'
        }
        diffed = Diffed(data, diff)
        diffed['flat'] = 3
        self.assertEqual(diffed['flat'], 3)
        self.assertEqual(diff['flat'], 3)
        self.assertEqual(data['flat'], 1)

    def test_complex_assign(self):
        data = {
            'nested': {
                'flat': 1
            }
        }
        diff = {}
        diffed = Diffed(data, diff)
        nested = diffed['nested']
        nested['flat'] = 2
        self.assertEqual(diffed['nested']['flat'], 2)
        self.assertEqual(data['nested']['flat'], 1)
        self.assertEqual(diff['nested']['flat'], 2)

    def test_list_assign(self):
        data = {
            'list': [1, 2, 3]
        }
        diffed = Diffed(data, {})
        diffed['list'] = []
        diffed.add_diff({})
        diffed['list'] = [5, 6]
        diffed.flatten()
        self.assertEqual(data['list'], [5, 6])

    def test_dict_view_get(self):
        data = {
            'nested': {'flat': 1}
        }
        first_diff = {
            'nested': DictView({'another_flat': 2})
        }
        last_diff = {}
        diffed = Diffed(data, (first_diff, last_diff))
        nested = diffed['nested']
        self.assertIsInstance(nested, Diffed)
        self.assertIn('nested', last_diff)
        self.assertNotIn('flat', nested)
        self.assertEqual(nested['another_flat'], 2)

    def test_del(self):
        data = {
            'flat': 1,
            'nested': {
                'flat': 1,
                'dict': {
                    'flat': 1
                }
            }
        }
        diff = {
        }
        diffed = Diffed(data, diff)
        del diffed['flat']
        self.assertNotIn('flat', diffed)
        self.assertIsNone(diff['flat'])

        nested = diffed['nested']
        del nested['flat']
        del nested['dict']
        self.assertIn('nested', diff)
        self.assertNotIn('flat', nested)
        self.assertNotIn('dict', nested)


    def test_dump(self):
        data = {
            'flat': 1,
            'list': [1, 2, 3],
            'dict': {'field': 1, 'deleted': 1},
            'deleted': {'field': 1},
        }
        diffed = Diffed(data)
        dump = dump_value(diffed)
        self.assertEqual(dump['flat'], 1)
        self.assertIsInstance(dump['list'], list)
        self.assertIsInstance(dump['dict'], dict)

        diff = {
            'flat': 2,
            'list': [4, 5],
            'dict': {'diffed_field': 3, 'deleted': None},
            'deleted': None
        }
        diffed.add_diff(diff)
        dump = dump_value(diffed)
        self.assertEqual(dump['flat'], 2)
        self.assertIn('field', dump['dict'])
        self.assertIn('diffed_field', dump['dict'])
        self.assertNotIn('deleted', dump)
        self.assertNotIn('deleted', dump['dict'])


if __name__ == '__main__':
    unittest.main()
