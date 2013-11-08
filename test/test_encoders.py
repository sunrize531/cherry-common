from cherrycommon.dictutils import encode_data, decode_data, AMF, JSON, XJSON, YAML
import unittest


class EncoderTest(unittest.TestCase):
    src = {
        'plain': 1,
        'nested': {
            'plain': 1,
            'list': [1, 2]
        },
        'list': [1, 2, 3]
    }

    def _is_match(self, re):
        self.assertEquals(re['plain'], self.src['plain'])
        self.assertEquals(re['nested'], self.src['nested'])
        self.assertEquals(re['list'].index(1), 0)

    def test_amf(self):
        re = decode_data(encode_data(self.src, AMF), AMF)
        self._is_match(re)

    def test_json(self):
        re = decode_data(encode_data(self.src, JSON), JSON)
        self._is_match(re)

    def test_xjson(self):
        re = decode_data(encode_data(self.src, XJSON), XJSON)
        self._is_match(re)


if __name__ == '__main__':
    unittest.main()