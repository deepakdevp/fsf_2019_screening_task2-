from PyQt5 import uic, QtCore
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QTableWidgetItem, QDialog, \
    QMessageBox, QVBoxLayout, QCheckBox, QProgressDialog, QInputDialog, QLineEdit
import csv
class CsvLoaderWorker(QObject):
    workRequested = pyqtSignal()
    finished = pyqtSignal()
    relay = pyqtSignal(int)
    progress_max = pyqtSignal(int)
    update_bottom_toolbar = pyqtSignal()
    def __init__(self, csv_file_path, csv_data_table, column_headers, column_headers_all, parent=None):
        super(CsvLoaderWorker, self).__init__(parent)
        self.csv_file_path = csv_file_path
        self.csv_data_table = csv_data_table
        self.column_headers = column_headers
        self.column_headers_all = column_headers_all
    def processLoadingFile(self):
        column_headers = []
        column_headers_all = []
        with open(self.csv_file_path[0], newline='') as csv_file:
            self.progress_max.emit(len(csv_file.readlines()) - 2)

        with open(self.csv_file_path[0], newline='') as csv_file:

            self.csv_data_table.setRowCount(0)
            self.csv_data_table.setColumnCount(0)

            csv_file_read = csv.reader(csv_file, delimiter=',', quotechar='|')
            column_headers = next(csv_file_read)
            for header in column_headers:
                self.column_headers.append(header)
                self.column_headers_all.append(header)

            for row_data in csv_file_read:

                self.relay.emit(self.csv_data_table.rowCount())
                row = self.csv_data_table.rowCount()
                self.csv_data_table.insertRow(row)
                self.csv_data_table.setColumnCount(len(row_data))
                for column, stuff in enumerate(row_data):
                    item = QTableWidgetItem(stuff)
                    self.csv_data_table.setItem(row, column, item)

            self.csv_data_table.setHorizontalHeaderLabels(self.column_headers)
        self.csv_data_table.setWordWrap(False)
        self.csv_data_table.resizeRowsToContents()
        self.update_bottom_toolbar.emit()
        self.finished.emit()
    def requestWork(self):
        self.workRequested.emit()
