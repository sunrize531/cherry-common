from cherrycommon.dictutils import get_value, set_value
import unittest


class TestGetValue(unittest.TestCase):
    def test_dict_access(self):
        document = {
            'int_field': 1,
            'str_field': 'str',
            'nested_field': {
                'int_field': 1,
                'str_field': 'str'
            }
        }

        self.assertEqual(get_value(document, 'int_field'), 1)
        self.assertEqual(get_value(document, 'nested_field.int_field'), 1)

    def test_list_access(self):
        document = {
            'int_field': 1,
            'str_field': 'str',
            'nested_list': (1, 'str', {'list_field': 1})
        }
        self.assertEqual(get_value(document, 'nested_list[0]'), 1)
        self.assertEqual(get_value(document, 'nested_list[1]'), 'str')
        self.assertEqual(get_value(document, 'nested_list[2].list_field'), 1)
        self.assertRaises(TypeError, get_value, document, 'nested_list.0')
        self.assertRaises(TypeError, get_value, document, 'nested_list.1')

    def test_set_value(self):
        document = {
            'nested_field': {
                'int_field': 1
            },
            'nested_list': [1, 'str', {'list_field': 1}]
        }
        set_value(document, 'nested_field.int_field', 2)
        set_value(document, 'nested_field.str_field', 'str')
        set_value(document, 'new_nested_field.int_field', 1)
        set_value(document, 'nested_list[2].list_field', 2)
        set_value(document, 'new_nested_list[3]', 2)

        self.assertEqual(get_value(document, 'nested_field.int_field'), 2)
        self.assertEqual(get_value(document, 'nested_field.str_field'), 'str')
        self.assertEqual(get_value(document, 'new_nested_field.int_field'), 1)
        self.assertEqual(get_value(document, 'nested_list[2].list_field'), 2)
        self.assertEqual(get_value(document, 'new_nested_list[0]'), None)
        self.assertEqual(get_value(document, 'new_nested_list[3]'), 2)

    def test_flatten(self):
        document = {
            'str_int_field': '1',
            'str_round_field': '1.0',
            'str_float_field': '1.5',
            'str_field': 'str'
        }

        self.assertIsInstance(get_value(document, 'str_int_field', flatten=False), unicode)
        self.assertIsInstance(get_value(document, 'str_round_field', flatten=False), unicode)
        self.assertIsInstance(get_value(document, 'str_float_field', flatten=False), unicode)
        self.assertIsInstance(get_value(document, 'str_field', flatten=False), unicode)

        self.assertIsInstance(get_value(document, 'str_int_field', flatten=True), int)
        self.assertIsInstance(get_value(document, 'str_round_field', flatten=True), int)
        self.assertIsInstance(get_value(document, 'str_float_field', flatten=True), float)
        self.assertIsInstance(get_value(document, 'str_field', flatten=True), unicode)


if __name__ == '__main__':
    unittest.main()
