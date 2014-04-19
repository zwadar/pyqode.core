#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
logging.basicConfig(level=logging.INFO)
import mimetypes
import os
import sys

from PyQt4 import QtCore, QtGui

from pyqode.core import frontend
from pyqode.core.frontend import modes
from pyqode.core.frontend import panels
from pyqode.core import style

from ui.simple_editor_ui import Ui_MainWindow


class SimpleEditorWindow(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        # add panels
        frontend.install_panel(self.editor, panels.LineNumberPanel())
        frontend.install_panel(self.editor, panels.SearchAndReplacePanel(),
                          panels.SearchAndReplacePanel.Position.BOTTOM)
        # add modes
        frontend.install_mode(self.editor, modes.AutoCompleteMode())
        frontend.install_mode(self.editor, modes.CaseConverterMode())
        frontend.install_mode(self.editor, modes.FileWatcherMode())
        frontend.install_mode(self.editor, modes.CaretLineHighlighterMode())
        frontend.install_mode(self.editor, modes.RightMarginMode())
        frontend.install_mode(self.editor, modes.PygmentsSyntaxHighlighter(
            self.editor.document()))
        frontend.install_mode(self.editor, modes.ZoomMode())
        frontend.install_mode(self.editor, modes.CodeCompletionMode())
        frontend.install_mode(self.editor, modes.AutoIndentMode())
        frontend.install_mode(self.editor, modes.IndenterMode())
        frontend.install_mode(self.editor, modes.SymbolMatcherMode())

        # start pyqode server for our code editor widget
        frontend.start_server(self.editor, 'server.py')

        # connect to editor signals
        self.editor.dirty_changed.connect(self.actionSave.setEnabled)
        self.actionSave.triggered.connect(self.save)

        # create edit menu
        mnu = QtGui.QMenu("Edit", self.menubar)
        mnu.addActions(self.editor.actions())
        self.menubar.addMenu(mnu)
        self.setupModesMenu()
        self.setupPanelsMenu()
        self.setupStylesMenu()

        # open this module file in the editor
        frontend.open_file(self.editor, __file__)

    def setupStylesMenu(self):
        group = QtGui.QActionGroup(self)
        currentStyle = frontend.get_mode(self.editor,
            modes.PygmentsSyntaxHighlighter).pygments_style
        group.triggered.connect(self.on_style_changed)
        for style in sorted(modes.PYGMENTS_STYLES):
            a = QtGui.QAction(self.menuStyles)
            a.setText(style)
            a.setCheckable(True)
            if style == currentStyle:
                a.setChecked(True)
            group.addAction(a)
            self.menuStyles.addAction(a)

    def setupModesMenu(self):
        # Add modes to the modes menu
        for k, v in sorted(frontend.get_modes(self.editor).items()):
            a = QtGui.QAction(self.menuModes)
            a.setText(k)
            a.setCheckable(True)
            a.setChecked(True)
            a.changed.connect(self.on_mode_state_changed)
            a.mode = v
            self.menuModes.addAction(a)

    def setupPanelsMenu(self):
        for zones, panel_dic in sorted(frontend.get_panels(self.editor).items()):
            for k, v in panel_dic.items():
                a = QtGui.QAction(self.menuModes)
                a.setText(k)
                a.setCheckable(True)
                a.setChecked(True)
                a.changed.connect(self.on_panel_state_changed)
                a.panel = v
                self.menuPanels.addAction(a)

    @QtCore.pyqtSlot(QtGui.QAction)
    def on_style_changed(self, action):
        style.pygments_style = action.text()
        self.editor.refresh_style()

    @QtCore.pyqtSlot()
    def on_actionOpen_triggered(self):
        filePath = QtGui.QFileDialog.getOpenFileName(
            self, "Choose a file", os.path.expanduser("~"))
        if filePath:
            frontend.open_file(self.editor, filePath)

    def on_panel_state_changed(self):
        action = self.sender()
        action.panel.enabled = action.isChecked()

    def on_mode_state_changed(self):
        action = self.sender()
        action.mode.enabled = action.isChecked()

    @QtCore.pyqtSlot()
    def save(self):
        frontend.save_to_file(self.editor)


def main():
    # setup some specific mimetypes
    mimetypes.add_type('text/xml', '.ui')  # qt designer ui forms
    mimetypes.add_type('text/x-rst', '.rst')  # rst docs
    mimetypes.add_type('text/x-cython', '.pyx')  # cython impl files
    mimetypes.add_type('text/x-cython', '.pxd')  # cython def files
    if sys.platform == 'win32':
        # windows systems do not have a mimetypes for most of the codes python,
        # you have to add them all explicitely on windows, otherwise there
        # won't be any syntax highlighting
        mimetypes.add_type('text/x-python', '.py')
        mimetypes.add_type('text/x-python', '.pyw')
        mimetypes.MimeTypes().read_windows_registry()

    app = QtGui.QApplication(sys.argv)
    win = SimpleEditorWindow()
    win.show()
    app.exec_()
    # cleanup
    frontend.stop_server(win.editor)  # ensure the server is properly closed.
    del win
    del app

if __name__ == "__main__":
    main()