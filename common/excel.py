from RPA.Excel.Files import Files

class Excel:
    def __init__(self):
        self.excel = Files()

    def create_excel_file(self, filename, data):
        self.excel.create_workbook(filename, sheet_name='Results')
        self.excel.append_rows_to_worksheet(data, 'Results', True)
        self.excel.save_workbook()
        self.excel.close_workbook()

