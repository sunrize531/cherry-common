from cherrycommon.db import DataProvider
import unittest


class TestDataProvider(unittest.TestCase):
    def setUp(self):
        provider = DataProvider('cherry_common_unittest', 'documents')
        provider.remove()
        provider.insert([
            {'_id': '1', 'value': 1},
            {'_id': '2', 'value': 2},
            {'_id': '3', 'value': 3}
        ])
        self.provider = provider

    def tearDown(self):
        self.provider.remove()

    def test_insert(self):
        provider = self.provider

        self.assertEqual(provider['1']['value'], 1)
        self.assertEqual(provider['2']['value'], 2)
        self.assertEqual(provider['3']['value'], 3)

        provider.insert({'_id': 4, 'value': 4})
        self.assertEqual(provider[4]['value'], 4)

    def test_update(self):
        provider = self.provider
        provider.update({}, {'$set': {'value': 4}}, multi=True)
        self.assertEqual(provider['1']['value'], 4)
        self.assertEqual(provider['2']['value'], 4)
        self.assertEqual(provider['3']['value'], 4)

        provider.update('1', {'$set': {'value': 1}})
        self.assertEqual(provider['1']['value'], 1)


if __name__ == '__main__':
    unittest.main()
