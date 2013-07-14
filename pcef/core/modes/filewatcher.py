
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# PCEF - Python/Qt Code Editing Framework
# Copyright 2013, Colin Duquesnoy <colin.duquesnoy@gmail.com>
#
# This software is released under the LGPLv3 license.
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
Contains the mode that control the external changes of file.
"""
import hashlib
import os
import subprocess
import time
from pcef.core.system import JobRunner
from pcef.qt import QtCore, QtGui
from pcef.core import constants
from pcef.core.mode import Mode


class FileWatcher(Mode):

    """
    FileWatcher mode. (Verify the external changes from opened file)
    """
    #: Mode identifier
    IDENTIFIER = "FileWatcher"
    #: Mode description
    DESCRIPTION = "Verify if file is modified externally."

    def __init__(self):
        super(FileWatcher, self).__init__()
        self.__filesystemwatcher = QtCore.QFileSystemWatcher()
        self.__flgNotify = False
        self.__changeWaiting = False
        self.__filesystemwatcher.fileChanged.connect(self.__onFileChanged)

    def __notifyChange(self):
        self.__flgNotify = True
        ret = QtGui.QMessageBox.question(
            self.editor, "File changed",
            "The file <i>%s</i> has has changed externally.\n"
            "Do you want reload it?" % os.path.basename(
                self.editor.filePath),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if ret == QtGui.QMessageBox.Yes:
            self.editor.openFile(self.editor.filePath)
        self.__changeWaiting = False
        self.__flgNotify = False

    def __onFileChanged(self):
        self.__changeWaiting = True
        if self.editor.hasFocus() and self.__flgNotify:
            self.__notifyChange()

    @QtCore.Slot()
    def __onEditorFilePathChanged(self):
        path = self.editor.filePath
        if path not in self.__filesystemwatcher.files():
            self.__filesystemwatcher.addPath(path)

    @QtCore.Slot()
    def __onEditorFocusIn(self):
        if self.__changeWaiting:
            self.__notifyChange()

    def onStateChanged(self, state):
        """
        Connects/Disconnects to the mouseWheelActivated and keyPressed event
        """
        if state is True:
            self.editor.textSaved.connect(self.__onEditorFilePathChanged)
            self.editor.newTextSet.connect(self.__onEditorFilePathChanged)
            self.editor.focusedIn.connect(self.__onEditorFocusIn)
        else:
            self.editor.textSaved.disconnect(self.__onEditorFilePathChanged)
            self.editor.newTextSet.disconnect(self.__onEditorFilePathChanged)
            self.editor.focusedIn.disconnect(self.__onEditorFocusIn)
            self.__filesystemwatcher.removePath(self.editor.filePath)


if __name__ == '__main__':
    from pcef.core import QGenericCodeEdit, TextDecoration

    class Example(QGenericCodeEdit):

        def __init__(self):
            QGenericCodeEdit.__init__(self, parent=None)
            self.installMode(FileWatcher())
            self.openFile(__file__)
            self.resize(QtCore.QSize(1000, 600))

        def closeEvent(self, evt):
            print("closing")
            self.uninstallMode(FileWatcher)

    import sys
    app = QtGui.QApplication(sys.argv)
    e = Example()
    e.show()
    sys.exit(app.exec_())