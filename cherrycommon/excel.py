from json import dumps, loads
from types import NoneType
from cherrycommon.dictutils import flatten_value

__author__ = 'sunrize'

from xlwt import Formula
from xlwt.Style import easyxf
from xlwt.Workbook import Workbook as WtWorkbook

from xlrd import open_workbook


HEADER = 'header'
CELL = 'cell'

_CELL_FORMAT = 'font: name courier;'
_HEADER_FORMAT = 'font: name courier; pattern: pattern solid, fore_color light_yellow; protection: cell_locked on;'


def write_cell_value(value):
    value = flatten_value(value)
    if isinstance(value, (float, int, long, unicode, NoneType, Formula)):
        return value
    else:
        return dumps(value)


def read_cell_value(value):
    if value == '':
        return None
    try:
        value = loads(value)
    except (TypeError, ValueError):
        pass
    else:
        if isinstance(value, (dict, list, basestring)):
            return flatten_value(value)

    try:
        value = float(value)
    except ValueError:
        return value
    else:
        int_value = int(value)
        if int_value == value:
            return int_value
        else:
            return value


class XLS(object):
    _base = 26
    _A = 65

    @classmethod
    def get_column_name(cls, n):
        n = int(n) + 1
        s = ""
        while n:
            s += chr((n - 1) % cls._base + cls._A)
            n //= cls._base + 1
        return s[::-1]

    @classmethod
    def get_cell_name(cls, column, row):
        """
        This method will transform all good cell coordinates to mf excel AA12 form. Use it for formulas.
        """
        #Convert column number to Excel name.
        return '{}{}'.format(cls.get_column_name(column), row + 1)

    def __init__(self):
        self._sheets = []

    def add_sheet(self, name):
        sheet = Sheet(name)
        self._sheets.append(sheet)
        return sheet

    def get_sheet(self, name):
        try:
            return filter(lambda sheet: sheet.name == name, self._sheets)[0]
        except IndexError:
            raise KeyError('Sheet with name "{}" not found.'.format(name))

    def write(self, stream):
        wb = WtWorkbook()
        for sheet in self._sheets:
            sheet.write(wb)
        wb.save(stream)

    def read(self, content):
        wb = open_workbook(file_contents=content, formatting_info=True)
        xf_list = wb.xf_list
        for s in wb.sheets():
            sheet = self.add_sheet(s.name)
            for r in range(0, s.nrows):
                sheet_row = s.row(r)
                if sheet_row:
                    row_style = xf_list[sheet_row[0].xf_index]
                    pattern = row_style.background.fill_pattern
                    if pattern:
                        style = HEADER
                    else:
                        style = CELL
                    sheet.add_row(map(lambda cell: read_cell_value(cell.value), sheet_row), style)


class Sheet(object):
    def __init__(self, name):
        self.name = name
        self.rows = []

    def add_row(self, data, style=CELL):
        row = Row(data, style)
        self.rows.append(row)
        return row

    @property
    def num_rows(self):
        return len(self.rows)

    _styles = {}

    @classmethod
    def get_style(cls, style):
        try:
            return cls._styles[style]
        except KeyError:
            pass

        if style == CELL:
            _xf_style = easyxf(_CELL_FORMAT)
            cls._styles[CELL] = _xf_style
        elif style == HEADER:
            _xf_style = easyxf(_HEADER_FORMAT)
            cls._styles[HEADER] = _xf_style
        else:
            raise ValueError('Allowed styles are "head", "cell". Got {}.'.format(style))

        return _xf_style

    def write(self, wb):
        ws = wb.add_sheet(self.name)
        col_widths = {}
        for row_num, row in enumerate(self.rows):
            style = self.get_style(row.style)
            for cell_num, value in enumerate(row.cells):
                value = write_cell_value(value)
                ws.write(row_num, cell_num, value, style)
                if not isinstance(value, Formula):
                    col_widths[cell_num] = min(max(col_widths.get(cell_num, 10), len(unicode(value))), 54)

        for num, width in col_widths.iteritems():
            ws.col(num).width = width * 256 * 1.2


class Row(object):
    def __init__(self, cells, style=CELL):
        self.cells = cells
        self.style = style
