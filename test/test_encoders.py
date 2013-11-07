from cherrycommon.excel import XLS
import unittest


class ExcelTest(unittest.TestCase):
    def test_cell_names(self):
        self.assertEqual(XLS.get_cell_name(0, 0), 'A1')
        self.assertEqual(XLS.get_cell_name(25, 0), 'Z1')
        self.assertEqual(XLS.get_cell_name(26, 9), 'AA10')


if __name__ == '__main__':
    unittest.main()