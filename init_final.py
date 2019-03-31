import os
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from PyQt5 import uic, QtCore
import loader
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QTableWidgetItem, QDialog, \
    QMessageBox, QVBoxLayout, QCheckBox, QProgressDialog, QInputDialog, QLineEdit
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.interpolate import make_interp_spline
class CsvEditor(QMainWindow):
    def __init__(self):
        super(CsvEditor, self).__init__()
        abs_file_name = os.path.dirname(__file__)
        mainwindowui_file = os.path.join(abs_file_name, "ui/mainwindow.ui")
        uic.loadUi(mainwindowui_file, self)
        self.tableTab = self.main_document_tab
        self.start_page_tab = self.start_tab
        self.plot_page_tab = self.plot_tab
        self.tabWidget.setCurrentIndex(0)
        self.action_column_layout.setEnabled(False)
        self.action_add_data.setEnabled(False)
        self.action_add_column.setEnabled(False)
        self.action_toolbar_add_data.setEnabled(False)
        self.action_edit_data.setEnabled(False)
        self.action_delete_selected.setEnabled(False)
        self.action_toolbar_delete_selected.setEnabled(False)
        self.action_close_file.setEnabled(False)
        self.check_cell_change = True
        self.file_changed = False
        self.setSaveEnabled(False)
        self.setPlotOptions(False)
        self.set_connections()
        self.tabWidget.removeTab(2)
        self.tabWidget.removeTab(1)

        self.plot_inverted = False
        self.figure = None

        self.column_visibility_dialog_reference = None
        self.setBottomToolbarInfo(default_values=True)
        self.show()
    def set_connections(self):
        self.action_column_layout.triggered.connect(self.openColumnLayoutDialog)
        self.csv_data_table.cellChanged.connect(self.cellChangeCurrent)
        self.csv_data_table.itemSelectionChanged.connect(self.cellSelectionChanged)

        self.action_load_file.triggered.connect(self.loadCsv)
        self.action_toolbar_open_file.triggered.connect(self.loadCsv)
        self.btn_load_csv.clicked.connect(self.loadCsv)


        self.action_toolbar_save_file.triggered.connect(self.saveFile)
        self.action_save_file.triggered.connect(self.saveFile)

        # Radiobox for plotting axes flipped or not
        ########## Remove this function
        #self.radio_plot_xy.toggled.connect(self.flip_plot_axes)

        # Plot toolbar functions
        self.action_toolbar_plot_scatter_points.triggered.connect(self.plotScatterPoints)
        self.action_toolbar_plot_scatter_points_lines.triggered.connect(self.plotScatterPointsLines)
        self.action_toolbar_plot_lines.triggered.connect(self.plotLines)
        self.action_plot_scatter_points.triggered.connect(self.plotScatterPoints)
        self.action_plot_scatter_points_lines.triggered.connect(self.plotScatterPointsLines)
        self.action_plot_lines.triggered.connect(self.plotLines)

        # Close plot function
        self.btn_close_plot.clicked.connect(self.close_plot_tab)

        # Save plot function
        self.btn_save_plot.clicked.connect(self.save_plot_as_png)
        self.action_save_plot_png.triggered.connect(self.save_plot_as_png)
        self.action_toolbar_save_plot_png.triggered.connect(self.save_plot_as_png)

        # Set plot title
        self.plot_title = 'Title'
        self.btn_set_plot_title.clicked.connect(self.setPlotTitle)

        # Add data function
        self.action_add_data.triggered.connect(self.addBlankDataRow)
        self.action_toolbar_add_data.triggered.connect(self.addBlankDataRow)
        self.action_add_column.triggered.connect(self.addBlankDataColumn)

        # Delete data function
        self.action_toolbar_delete_selected.triggered.connect(self.deleteSelection)
        self.action_delete_selected.triggered.connect(self.deleteSelection)

        # Edit data menu item function
        self.action_edit_data.triggered.connect(self.editCurrentCell)

        # Close file function
        self.action_close_file.triggered.connect(self.close_file)

        # Exit the app
        self.action_exit.triggered.connect(self.closeEvent)

    # Threaded functions for multi threading the loading for handling large files
    def on_loading_finish(self):
        # Change the cursor back to normal
        QApplication.restoreOverrideCursor()
        self.loading_thread.quit()

    def update_loading_progress(self, value):
        self.loading_progress.setValue(value)

    def set_maximum_progress_value(self, max_value):
        print(max_value)
        self.loading_progress.setMaximum(max_value)
        self.loading_progress.setValue(0)

    def loadCsv(self):
        """
        Loads the file from file selector to a table
        closes any open file if any before opening new file
        """
        # Close any already opened file if any
        self.close_file()

        # Disable cell change check to avoid crashes
        self.check_cell_change = False

        # Set the flag to no changes in current file state
        self.file_changed = False
        self.setSaveEnabled(False)

        csv_file_path = QFileDialog.getOpenFileName(self, "Load CSV File", "", 'CSV(*.csv)')

        # Proceed if and only if a valid file is selected and the file dialog is not cancelled
        if csv_file_path[0]:
            # Get only the file name from path. eg. 'data_file.csv'
            filepath = os.path.normpath(csv_file_path[0])
            filename = filepath.split(os.sep)
            self.csv_file_name = filename[-1]

            self.loading_progress = QProgressDialog("Reading Rows. Please wait...", None, 0, 100, self)
            self.loading_progress.setWindowTitle("Loading CSV File...")
            self.loading_progress.setCancelButton(None)

            # enable custom window hint
            self.loading_progress.setWindowFlags(self.loading_progress.windowFlags() | QtCore.Qt.CustomizeWindowHint)
            # disable (but not hide) close button
            self.loading_progress.setWindowFlags(self.loading_progress.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

            # Show waiting cursor till the time file is being processed
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            self.loading_worker = loader.CsvLoaderWorker(csv_file_path=csv_file_path, csv_data_table=self.csv_data_table,
                                                  column_headers=self.column_headers,
                                                  column_headers_all=self.column_headers_all)

            self.loading_thread = QThread()
            # Set higher priority to the GUI Thread so UI remains a bit smoother
            QThread.currentThread().setPriority(QThread.HighPriority)

            self.loading_worker.moveToThread(self.loading_thread)
            self.loading_worker.workRequested.connect(self.loading_thread.start)
            self.loading_thread.started.connect(self.loading_worker.processLoadingFile)
            self.loading_worker.finished.connect(self.on_loading_finish)

            self.loading_worker.relay.connect(self.update_loading_progress)
            self.loading_worker.progress_max.connect(self.set_maximum_progress_value)
            self.loading_worker.update_bottom_toolbar.connect(self.setBottomToolbarInfo)

            self.loading_progress.setValue(0)
            self.loading_worker.requestWork()

            self.check_cell_change = True

            # Close the start page tab and load the file tab
            self.tabWidget.removeTab(0)
            self.tabWidget.insertTab(1, self.tableTab, "Main Document")

            # Enable Column Layout menu option
            self.action_column_layout.setEnabled(True)
            self.action_add_data.setEnabled(True)
            self.action_add_column.setEnabled(True)
            self.action_toolbar_add_data.setEnabled(True)
            self.action_close_file.setEnabled(True)

    def addBlankDataRow(self):
        lastRowCount = self.csv_data_table.rowCount()
        columnCount = self.csv_data_table.columnCount()
        self.csv_data_table.insertRow(lastRowCount)
        for emptyCol in range(0, columnCount):
            item = QTableWidgetItem('')
            self.csv_data_table.setItem(lastRowCount, emptyCol, item)
        
    def addBlankDataColumn(self):
        header_title, ok_pressed = QInputDialog.getText(self, "Add Column", "Enter heading for the column:",
                                                        QLineEdit.Normal, "")
        if ok_pressed and header_title != '':
            default_value, set_default_pressed = QInputDialog.getText(self, "Set Default Value",
                                                                      "Enter default value to set for column if any:",
                                                                      QLineEdit.Normal, "")

            rowCount = self.csv_data_table.rowCount()
            lastColumnCount = self.csv_data_table.columnCount()
            self.csv_data_table.insertColumn(lastColumnCount)
            for emptyRow in range(0, rowCount):
                item = QTableWidgetItem(default_value)
                self.csv_data_table.setItem(emptyRow, lastColumnCount, item)
            self.column_headers.append(header_title)
            self.column_headers_all.append(header_title)
            self.csv_data_table.setHorizontalHeaderLabels(self.column_headers)
    def editCurrentCell(self):
        cells = self.csv_data_table.selectionModel().selectedIndexes()
        if len(cells) == 1:
            for cell in sorted(cells):
                r = cell.row()
                c = cell.column()
                self.csv_data_table.editItem(self.csv_data_table.item(r, c))
    def deleteSelection(self):
        selected_columns = sorted(self.selected_columns, reverse=True)
        selected_rows = sorted(self.selected_rows, reverse=True)
        fileChanged = False
        if len(selected_rows) > 0 or len(selected_columns) > 0:
            self.file_changed = True
            self.setSaveEnabled(True)
            
        for col in selected_columns:
            header_value = self.csv_data_table.horizontalHeaderItem(col).text()
            if header_value in self.column_headers_all:
                self.column_headers_all.remove(header_value)
            if header_value in self.column_headers:
                self.column_headers.remove(header_value)
            try:
                self.column_visibility_dialog_reference.removeHeader(header_value)
            except:
                pass
            self.csv_data_table.removeColumn(col)

        self.selected_columns.clear()
        for row in selected_rows:
            self.csv_data_table.removeRow(row)

        self.selected_rows.clear()
        cells = self.csv_data_table.selectionModel().selectedIndexes()

        if len(cells) > 0:
            self.file_changed = True
            self.setSaveEnabled(True)

        for cell in sorted(cells):
            r = cell.row()
            c = cell.column()
            self.csv_data_table.item(r, c).setText('')
        self.setBottomToolbarInfo()

    def openColumnLayoutDialog(self):
        if self.column_visibility_dialog_reference is None:
            self.column_visibility_dialog_reference = ColumnLayoutDialog()

        self.column_visibility_dialog_reference.addHeaderVisibleOptions(self.column_headers_all, self.column_headers)
        self.column_visibility_dialog_reference.setModal(True)
        self.column_visibility_dialog_reference.exec_()
        self.hideInvisibleHeaders()

    def setSaveEnabled(self, enabled):
        self.action_toolbar_save_file.setEnabled(enabled)
        self.action_save_file.setEnabled(enabled)

    def saveFile(self):
        file_save_path = QFileDialog.getSaveFileName(self, 'Save CSV', "", 'CSV(*.csv)')

        if file_save_path[0]:
            with open(file_save_path[0], 'w', newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.column_headers)
                for row in range(self.csv_data_table.rowCount()):
                    row_data = []
                    for column in range(self.csv_data_table.columnCount()):
                        if self.csv_data_table.isColumnHidden(column):
                            continue

                        item = self.csv_data_table.item(row, column)
                        if item is not None:
                            row_data.append(item.text())
                        else:
                            row_data.append('')
                    writer.writerow(row_data)
            self.file_changed = False
            self.setSaveEnabled(False)
            QMessageBox.about(self, "Success!", "Your file has been saved successfully.")

    def prompSaveBeforeClosing(self):
        if self.file_changed:
            choice = QMessageBox.question(self, 'Save File', "All your changes will be lost if you quit without saving.",
                                          QMessageBox.Yes | QMessageBox.No)
            if choice == QMessageBox.Yes:
                self.saveFile()
    def close_file(self):
        if self.file_changed:
            self.prompSaveBeforeClosing()

        self.setBottomToolbarInfo(default_values=True)
        self.action_column_layout.setEnabled(False)
        self.action_add_data.setEnabled(False)
        self.action_add_column.setEnabled(False)
        self.column_visibility_dialog_reference = None
        # Disable other file related options
        self.action_toolbar_add_data.setEnabled(False)
        self.action_close_file.setEnabled(False)

        self.column_headers_all = []
        self.column_headers = []

        # Clear the populated table
        self.csv_data_table.setRowCount(0)

        # Remove plot and file page tab
        try:
            # with each deletion index of the current tab decreases
            self.tabWidget.removeTab(0)
            self.tabWidget.removeTab(0)
            self.tabWidget.removeTab(0)
        except:
            pass

        self.tabWidget.insertTab(0, self.start_page_tab, "Start Page")
        # Disable the column layout option and enable only when csv is loaded
        self.action_column_layout.setEnabled(False)
        # Disable add data option and enable only when csv is loaded
        self.action_add_data.setEnabled(False)
        self.action_add_column.setEnabled(False)
        self.action_toolbar_add_data.setEnabled(False)
        self.action_edit_data.setEnabled(False)
        self.action_delete_selected.setEnabled(False)
        self.action_toolbar_delete_selected.setEnabled(False)
        self.action_close_file.setEnabled(False)
        self.action_save_file.setEnabled(False)

        self.setPlotOptions(False)

        # If user selected not to save changes, in this case var wont change to false withing prompt funtion
        self.file_changed = False
        self.setSaveEnabled(False)

    def closeEvent(self, QCloseEvent):
        self.prompSaveBeforeClosing()
        exit(0)
    def cellChangeCurrent(self):
        try:
            if self.check_cell_change:
                row = self.csv_data_table.currentRow()
                col = self.csv_data_table.currentColumn()
                value = self.csv_data_table.item(row, col).text()

                self.setBottomToolbarInfo()

        except:
            pass
        finally:
            if self.check_cell_change:
                self.file_changed = True
                self.setSaveEnabled(True)

    def cellSelectionChanged(self):
        self.cells_selected = self.csv_data_table.selectionModel().selectedIndexes()
        if len(self.cells_selected) == 1:
            self.action_edit_data.setEnabled(True)
        else:
            self.action_edit_data.setEnabled(False)
        if len(self.cells_selected) >= 1:
            self.action_delete_selected.setEnabled(True)
            self.action_toolbar_delete_selected.setEnabled(True)
        else:
            self.action_delete_selected.setEnabled(False)
            self.action_toolbar_delete_selected.setEnabled(False)
        cols = self.csv_data_table.selectionModel().selectedColumns()
        self.selected_columns = []
        for index in sorted(cols):
            col = index.column()
            self.selected_columns.append(col)

        rows = self.csv_data_table.selectionModel().selectedRows()
        self.selected_rows = []
        for index in sorted(rows):
            row = index.row()
            self.selected_rows.append(row)

        self.setBottomToolbarInfo()

        if len(self.selected_columns) == 2:
            self.setPlotOptions(True)
        else:
            self.setPlotOptions(False)

    def hideInvisibleHeaders(self):
        col_index = 0
        for header in self.column_headers_all:
            if header in self.column_headers:
                self.csv_data_table.setColumnHidden(col_index, False)
                self.file_changed = True
                self.setSaveEnabled(True)
            else:
                self.csv_data_table.setColumnHidden(col_index, True)
            col_index = col_index + 1

    def setBottomToolbarInfo(self, default_values=False):
        if default_values:
            self.action_toolbar_bottom_column_count.setIconText("Column count -")
            self.action_toolbar_bottom_row_count.setIconText("Row count -")
            self.action_toolbar_bottom_source.setIconText("Source: No Source")
            self.action_toolbar_bottom_column.setIconText("Column -")
            self.action_toolbar_bottom_row.setIconText("Row -")
            self.action_toolbar_bottom_selected_cells.setIconText("Selected Cells -")
            self.action_toolbar_bottom_text_length.setIconText("Text Length -")
            self.cells_selected = []
            self.csv_file_name = 'No Source'
        else:
            self.action_toolbar_bottom_column_count.setIconText(
                "Column count " + str(self.csv_data_table.columnCount()))
            self.action_toolbar_bottom_row_count.setIconText("Row count " + str(self.csv_data_table.rowCount()))
            self.action_toolbar_bottom_source.setIconText("Source: " + self.csv_file_name)
            self.action_toolbar_bottom_column.setIconText("Column " + str(self.csv_data_table.currentColumn() + 1))
            self.action_toolbar_bottom_row.setIconText("Row " + str(self.csv_data_table.currentRow() + 1))
            self.action_toolbar_bottom_selected_cells.setIconText("Selected Cells " + str(len(self.cells_selected)))
        try:
            row = self.csv_data_table.currentRow()
            col = self.csv_data_table.currentColumn()
            value = self.csv_data_table.item(row, col).text()
        except:
            value = ''
        self.action_toolbar_bottom_text_length.setIconText("Text Length " + str(len(value)))

    def setPlotOptions(self, visibility):
        self.action_toolbar_plot_scatter_points.setEnabled(visibility)
        self.action_toolbar_plot_scatter_points_lines.setEnabled(visibility)
        self.action_toolbar_plot_lines.setEnabled(visibility)
        self.action_plot_scatter_points.setEnabled(visibility)
        self.action_plot_scatter_points_lines.setEnabled(visibility)
        self.action_plot_lines.setEnabled(visibility)
        self.action_save_plot_png.setEnabled(False)
        self.action_toolbar_save_plot_png.setEnabled(False)

    def plotScatterPoints(self):
        self.plot(1)

    def plotScatterPointsLines(self):
        self.plot(2)

    def plotLines(self):
        self.plot(3)

    def setPlotTitle(self):
        """
        Sets the plot title when the button is clicked with the value present in the title input box
        """
        plot_title = self.input_plot_title.text()
        if plot_title:
            self.plot_title = self.input_plot_title.text()
            # Redraw the plot with given title
            if not self.plot_inverted:
                self.drawPlot(self.data_x_axis, self.data_y_axis, self.label_x_axis, self.label_y_axis)
            else:
                self.drawPlot(self.data_y_axis, self.data_x_axis, self.label_y_axis, self.label_x_axis)
        else:
            QMessageBox.about(self, "Error!", "Please enter a title to set in the plot")
    def plot(self, plotType):
        """
        The parent function for setting parameters for plotting and calling the draw function to render the plot
        :param plotType: defines which type of plot is to be rendered
        """
        # Build plotting data
        self.data_x_axis = []
        self.data_y_axis = []
        for i in range(0, self.csv_data_table.rowCount()):
            value = self.csv_data_table.item(i, self.selected_columns[0]).text()
            self.data_x_axis.append(value)
            value = self.csv_data_table.item(i, self.selected_columns[1]).text()
            self.data_y_axis.append(value)

        self.label_x_axis = self.csv_data_table.horizontalHeaderItem(self.selected_columns[0]).text()
        self.label_y_axis = self.csv_data_table.horizontalHeaderItem(self.selected_columns[1]).text()

        # Avoid duplication of resources if already allocated
        if self.figure is None:
            self.figure = plt.figure()
            self.canvas = FigureCanvas(self.figure)

            # self.plot_frame_horizontal.addStretch()
            self.plot_frame_horizontal.addWidget(self.canvas)
            # self.plot_frame_horizontal.addStretch()

        # Ensures only 2 tabs at max are open at a time - file and plot tabs respectively
        if self.tabWidget.count() == 1:
            self.tabWidget.insertTab(1, self.plot_page_tab, "Plot")

        self.tabWidget.setCurrentIndex(1)

        self.plotType = plotType

        try:
            for i in range(0, len(self.data_x_axis)):
                if self.data_x_axis[i] == '':
                    self.data_x_axis[i] = 0
                if self.data_y_axis[i] == '':
                    self.data_y_axis[i] = 0

                self.data_x_axis[i] = self.strToNumber(self.data_x_axis[i])
                self.data_y_axis[i] = self.strToNumber(self.data_y_axis[i])

            self.data_x_axis = np.array(self.data_x_axis)
            self.data_y_axis = np.array(self.data_y_axis)

            print(self.data_x_axis)
            print(self.data_y_axis)

        except:
            pass
            print("In generic plotting")

        self.drawPlot(self.data_x_axis, self.data_y_axis, self.label_x_axis, self.label_y_axis)
    def isfloat(self, x):
        try:
            a = float(x)
        except ValueError:
            return False
        else:
            return True

    def isint(self, x):
        try:
            a = float(x)
            b = int(a)
        except ValueError:
            return False
        else:
            return a == b

    def strToNumber(self, x):
        if self.isint(x):
            x = int(x)
            return x
        elif self.isfloat(x):
            x = float(x)
            return x
        else:
            raise ("cant coerce")

    def drawPlot(self, data_x_axis, data_y_axis, label_x_axis, label_y_axis):

        self.figure.clear()
        self.figure.tight_layout()
        self.figure.subplots_adjust(left=0.1, right=0.9, bottom=0.3, top=0.9)

        self.figure.suptitle(self.plot_title)

        ax = self.figure.add_subplot(111)
        ax.set_xlabel(label_x_axis)
        ax.set_ylabel(label_y_axis)

        ax.xaxis.set_major_locator(plt.MaxNLocator(10))
        ax.yaxis.set_major_locator(plt.MaxNLocator(10))

        if self.plotType == 1:
            ax.scatter(data_x_axis, data_y_axis)

        elif self.plotType == 2:
            try:
                T = data_x_axis
                power = data_y_axis

                xnew = np.linspace(T.min(), T.max(),
                                   300)

                spl = make_interp_spline(T, power, k=3)
                power_smooth = spl(xnew)
                ax.scatter(data_x_axis, data_y_axis)
                ax.plot(xnew, power_smooth, marker='o')
            except:
                ax.plot(data_x_axis, data_y_axis, marker='o')

        else:
            ax.plot(data_x_axis, data_y_axis)

        self.canvas.draw()
        self.action_save_plot_png.setEnabled(True)
        self.action_toolbar_save_plot_png.setEnabled(True)

    def save_plot_as_png(self):
        file_save_path = QFileDialog.getSaveFileName(self, 'Save Plot PNG', "", "PNG (*.png)|*.png")

        if file_save_path[0]:
            self.figure.savefig(file_save_path[0], bbox_inches='tight')
            QMessageBox.about(self, "Success!", "Your plot has been saved as png image successfully.")

    def close_plot_tab(self):
        tmp_tab_reference = self.plot_page_tab
        self.tabWidget.removeTab(1)
        self.tabWidget.setCurrentIndex(0)
        self.plot_page_tab = tmp_tab_reference


# Dialog window for show/hide Column visibility feature
class ColumnLayoutDialog(QDialog):
    def __init__(self):
        super(ColumnLayoutDialog, self).__init__()

        abs_file_name = os.path.dirname(__file__)
        contentlayoutdialogui_file = os.path.join(abs_file_name, "ui/contentlayoutdialog.ui")
        uic.loadUi(contentlayoutdialogui_file, self)

        self.visible_headers_list = []

        self.btn_save_header_view.clicked.connect(self.saveHeaderList)

    def addHeaderVisibleOptions(self, header_list, visible_list):
        layout = QVBoxLayout()

        for header in header_list:
            print(header)
            check_box = QCheckBox(header)
            if self.visible_headers_list:
                if header in self.visible_headers_list:
                    check_box.setChecked(True)
                else:
                    check_box.setChecked(False)
            else:
                check_box.setChecked(True)
            layout.addWidget(check_box)

        self.column_layout_list_scroll_area.setLayout(layout)
        self.visible_headers_list = visible_list

    def saveHeaderList(self):
        self.visible_headers_list.clear()

        check_box_list = self.column_layout_list_scroll_area.findChildren(QCheckBox)
        for loop in range(len(check_box_list)):
            if check_box_list[loop].isChecked():
                self.visible_headers_list.append(check_box_list[loop].text())

    def removeHeader(self, header_title):
        if header_title in self.visible_headers_list:
            self.visible_headers_list.remove(header_title)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CsvEditor()
    window.show()
    sys.exit(app.exec_())
