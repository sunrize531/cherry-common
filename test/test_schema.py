from cherrycommon.dictutils import get_schema

__author__ = 'sunrize'

import unittest


class SchemaTest(unittest.TestCase):
    def test_nested(self):
        d = {
            'plain_field': 1,
            'nested_dict': {
                'nested_field_1': 1,
                'nested_field_2': 2
            },
            'nested_list': ['value_1', 'value_2']
        }

        nested_schema = get_schema(d)
        skip_nested_schema = get_schema(d, skip_nested=True)
        top_level_schema = get_schema(d, nested_level=0)

        self.assertIn('plain_field', skip_nested_schema)
        self.assertIn('plain_field', nested_schema)
        self.assertIn('plain_field', top_level_schema)

        self.assertNotIn('nested_dict', skip_nested_schema)
        self.assertIn('nested_dict', nested_schema)
        self.assertIn('nested_dict', top_level_schema)

        self.assertIn('nested_dict.nested_field_1', skip_nested_schema)
        self.assertIn('nested_dict.nested_field_1', nested_schema)
        self.assertNotIn('nested_dict.nested_field_1', top_level_schema)


if __name__ == '__main__':
    unittest.main()
