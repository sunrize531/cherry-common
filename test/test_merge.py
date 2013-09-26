from cherrycommon.dictutils import merge, DictView

__author__ = 'sunrize'

import unittest


class MergeTest(unittest.TestCase):
    def test_merge(self):
        nested = {
            'flat': 1
        }
        target = {
            'flat': 1,
            'nested': nested
        }
        source = {
            'flat': 2,
            'nested': {'flat': 2},
            'empty_view': DictView(),
            'empty_dict': {}
        }

        merged = merge(target, source)
        self.assertEqual(target['flat'], 2)
        self.assertEqual(nested['flat'], 2)
        self.assertIs(target['nested'], nested)
        self.assertIn('empty_view', merged)
        self.assertNotIn('empty_dict', merged)

    def test_dict_view(self):
        target = {
            'nested': {
                'field1': 1,
                'field2': 1,
                'field3': 1
            }
        }

        source = {
            'nested': DictView({
                'field1': 2
            })
        }
        merged = merge(target, source)
        self.assertEqual(merged['nested']['field1'], source['nested']['field1'])
        self.assertNotIn('field2', merged['nested'])
        self.assertNotIn('field3', merged['nested'])
        self.assertIsInstance(merged['nested'], dict)

    def test_types(self):
        target = {
            'str_field': '1',
            'numeric_field': 1.0
        }

        source = {
            'str_field': '2',
            'numeric_field': 2.0,
            'new_numeric_field': '2.1'
        }

        merged = merge(target, source)
        self.assertIsInstance(merged['str_field'], basestring)
        self.assertIsInstance(merged['numeric_field'], float)
        self.assertIsInstance(merged['new_numeric_field'], basestring)

    def test_keep_none(self):
        source = {
            'null_field': None,
            'empty_field': {},
            'nested': {'flat': 2},
        }

        merged = merge(source, {'nested': None}, keep_none=True)
        self.assertIn('nested', merged)

if __name__ == '__main__':
    unittest.main()
