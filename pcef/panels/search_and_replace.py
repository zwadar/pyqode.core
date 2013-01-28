#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# PCEF - PySide Code Editing framework
# Copyright 2013, Colin Duquesnoy <colin.duquesnoy@gmail.com>
#
# This software is released under the LGPLv3 license.
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
Contains the search and replace panel
"""
import logging
from PySide.QtCore import Qt
from PySide.QtCore import Signal
from PySide.QtCore import Slot
from PySide.QtGui import QColor
from PySide.QtGui import QBrush
from PySide.QtGui import QKeyEvent
from PySide.QtGui import QTextCursor
from PySide.QtGui import QTextDocument
from pygments.token import Text
from pcef.base import QEditorPanel
from pcef.base import TextDecoration
from pcef.qplaincodeedit import QPlainCodeEdit
from pcef.ui import search_panel_ui


class QSearchPanel(QEditorPanel):
    """
    Search (& replace) panel. Allow the user to search for content in the editor
    All occurrences are highlighted using the pygments syntax highlighter.
    The occurrence under the cursor is selected using the find method of the
    plain text edit. User can go backward and forward.

    The panel add a few actions to the editor menu(search, replace, next,
    previous, replace, replace all)

    The panel is show with ctrl-f for a search, ctrl-r for a search and replace.
    The panel is hidden with ESC or by using the close button (white cross).

    .. note:: The widget use a custom stylesheet similar to the search panel of
              Qt Creator.
    """
    #: Stylesheet
    QSS = """QWidget
    {
        background-color: %(bck)s;
        color: %(color)s;
    }

    QLineEdit
    {
        background-color: %(txt_bck)s;
        border: 1px solid %(highlight)s;
        border-radius: 3px;
    }

    QLineEdit:hover, QLineEdit:focus
    {
        border: 1px solid %(color)s;
        border-radius: 3px;
    }

    QPushButton
    {
        background-color: transparent;
    }

    QPushButton:hover
    {
        background-color: %(highlight)s;
        border: none;
        border-radius: 5px;
        color: %(color)s;
    }

    QPushButton:pressed
    {
        background-color: %(highlight)s;
        border: 2px black;
        border-radius: 5px;
        color: %(color)s;
    }

    QPushButton:disabled
    {
        color: %(highlight)s;
    }

    QCheckBox:hover
    {
            background-color: %(highlight)s;
            color: %(color)s;
            border-radius: 5px;
    }
    """

    #: Emitted when the nbr of occurences has changed
    numOccurrencesChanged = Signal()

    def __get_numOccurrences(self):
        return self._numOccurrences

    def __set_numOccurrences(self, numOccurrences):
        if self._numOccurrences != numOccurrences:
            self._numOccurrences = numOccurrences
            self.numOccurrencesChanged.emit()

    #: Nb occurences detected
    numOccurrences = property(__get_numOccurrences, __set_numOccurrences)

    def __init__(self, parent=None):
        QEditorPanel.__init__(self, "SearchPanel",
                              "The search and replace panel", parent)
        self.ui = search_panel_ui.Ui_SearchPanel()
        self.ui.setupUi(self)
        self._decorations = []
        self._numOccurrences = 0
        self._processing = False
        self.numOccurrencesChanged.connect(self.updateUi)
        self.ui.actionFindNext.triggered.connect(self.findNext)
        self.ui.actionFindPrevious.triggered.connect(self.findPrevious)
        self.ui.actionSearch.triggered.connect(self.showSearchPanel)
        self.ui.actionActionSearchAndReplace.triggered.connect(
            self.showSearchAndReplacePanel)
        self.hide()
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def showSearchPanel(self):
        """ Shows the search panel """
        self.show()
        self.ui.widgetSearch.show()
        self.ui.widgetReplace.hide()
        selectedText = self.editor.textEdit.textCursor().selectedText()
        if selectedText != "":
            self.ui.lineEditSearch.setText(selectedText)
        self.ui.lineEditSearch.setFocus()

    def showSearchAndReplacePanel(self):
        """ Shows the search and replace panel """
        self.show()
        self.ui.widgetSearch.show()
        self.ui.widgetReplace.show()
        selectedText = self.editor.textEdit.textCursor().selectedText()
        if selectedText != "":
            self.ui.lineEditSearch.setText(selectedText)
        self.ui.lineEditReplace.setFocus()

    def updateUi(self):
        """ Updates user interface (checkbox states, nb matches, ...) """
        # update matches label
        self.ui.labelMatches.setText("%d matches" % self.numOccurrences)
        color = "#CC0000"
        if self.numOccurrences > 0:
            color = "#00CC00"
        self.ui.labelMatches.setStyleSheet("color: %s" % color)

        # update replace buttons state
        replaceTxt = self.ui.lineEditReplace.text()
        enableReplace = (self.numOccurrences > 0 and replaceTxt != "")
        self.ui.pushButtonReplaceAll.setEnabled(enableReplace)
        self.ui.pushButtonReplace.setEnabled(enableReplace)

        # update navigation buttons state
        enableNavigation = (self.numOccurrences > 0)
        self.ui.pushButtonDown.setEnabled(enableNavigation)
        self.ui.pushButtonUp.setEnabled(enableNavigation)

    def _onStyleChanged(self):
        """ Change stylesheet """
        qss = self.QSS % {"bck": self.currentStyle.panelsBackgroundColor,
                          "txt_bck": self.currentStyle.backgroundColor,
                          "color": self.currentStyle.tokenColor(Text),
                          "highlight": self.currentStyle.panelSeparatorColor}
        self.setStyleSheet(qss)

    def install(self, editor):
        """  Install the panel on the editor """
        QEditorPanel.install(self, editor)
        self.editor.textEdit.cursorPositionChanged.connect(self.onCursorMoved)
        self.editor.textEdit.textChanged.connect(self.updateSearchResults)
        self.updateUi()
        self.installActions()

    def installActions(self):
        """ Installs actions on the editor context menu """
        editor = self.editor.textEdit
        assert isinstance(editor, QPlainCodeEdit)
        editor.addSeparator()
        editor.addAction(self.ui.actionSearch)
        editor.addAction(self.ui.actionActionSearchAndReplace)
        editor.addAction(self.ui.actionFindPrevious)
        editor.addAction(self.ui.actionFindNext)

    @Slot()
    def updateSearchResults(self):
        """  Updates the search results """
        txt = self.ui.lineEditSearch.text()
        self.highlightOccurrences(txt)

    def findNext(self):
        """ Finds the next occurrence """
        txt = self.ui.lineEditSearch.text()
        sf = self.getUserSearchFlag()
        if not self.editor.textEdit.find(txt, sf):
            # restart from start
            tc = self.editor.textEdit.textCursor()
            tc.movePosition(QTextCursor.Start)
            self.editor.textEdit.setTextCursor(tc)
            self.editor.textEdit.find(txt, sf)

    @Slot()
    def on_pushButtonDown_clicked(self):
        """ Finds the next occurrence """
        self.findNext()

    def findPrevious(self):
        """ Finds the previous occurrence """
        txt = self.ui.lineEditSearch.text()
        sf = self.getUserSearchFlag()
        sf |= QTextDocument.FindBackward
        if not self.editor.textEdit.find(txt, sf):
            # restart from end
            tc = self.editor.textEdit.textCursor()
            tc.movePosition(QTextCursor.End)
            self.editor.textEdit.setTextCursor(tc)
            self.editor.textEdit.find(self.ui.lineEditSearch.text(), sf)

    @Slot()
    def on_pushButtonUp_clicked(self):
        """ Finds the previous occurrence """
        self.findPrevious()

    @Slot()
    def on_pushButtonClose_clicked(self):
        """ Hides the panel """
        self.hide()
        self.ui.lineEditSearch.setText("")

    @Slot(int)
    def on_checkBoxCase_stateChanged(self, state):
        """ Re-highlight occurences """
        if self._processing is False:
            self.highlightOccurrences(self.ui.lineEditSearch.text())

    @Slot(int)
    def on_checkBoxWholeWords_stateChanged(self, state):
        """ Re-highlight occurences """
        if self._processing is False:
            self.highlightOccurrences(self.ui.lineEditSearch.text())

    def keyPressEvent(self, event):
        """ Handles key pressed: Return = next occurence, Esc = close panel """
        assert isinstance(event, QKeyEvent)
        if event.key() == Qt.Key_Escape:
            self.on_pushButtonClose_clicked()
        if event.key() == Qt.Key_Return:
            if self.ui.lineEditSearch.hasFocus():
                self.findNext()
            if self.ui.lineEditReplace.hasFocus():
                self.on_pushButtonReplace_clicked()

    @Slot(unicode)
    def on_lineEditSearch_textChanged(self, text):
        """ Re-highlight occurences """
        if self._processing is False:
            self.highlightOccurrences(text, True)

    @Slot(unicode)
    def on_lineEditReplace_textChanged(self, text):
        """ Updates user interface """
        self.updateUi()

    @Slot()
    def on_pushButtonReplace_clicked(self):
        """ Replace current selection and select first next occurence """
        txt = self.ui.lineEditReplace.text()
        self.editor.textEdit.insertPlainText(txt)
        self.selectFirst()

    @Slot()
    def on_pushButtonReplaceAll_clicked(self):
        """ Replace all occurences """
        txt = self.ui.lineEditReplace.text()
        if not self.ui.checkBoxCase.isChecked() and txt.upper() == self.ui.lineEditSearch.text().upper():
            return
        while self.numOccurrences > 0:
            self.editor.textEdit.insertPlainText(txt)
            self.selectFirst()

    def onCursorMoved(self):
        """ Re-highlight occurences """
        if self._processing is False:
            self.highlightOccurrences(self.ui.lineEditSearch.text())

    def selectFirst(self):
        """ Select the first next occurences """
        searchFlag = self.getUserSearchFlag()
        txt = self.ui.lineEditSearch.text()
        tc = self.editor.textEdit.textCursor()
        tc.movePosition(QTextCursor.Start)
        self.editor.textEdit.setTextCursor(tc)
        self.editor.textEdit.find(txt, searchFlag)

    def createDecoration(self, tc):
        """ Creates the text occurence decoration """
        deco = TextDecoration(tc)
        deco.setBackground(QBrush(QColor(
            self.currentStyle.searchBackgroundColor)))
        deco.setForeground(QBrush(QColor(
            self.currentStyle.searchColor)))
        return deco

    def highlightAllOccurrences(self):
        """ Highlight all occurrences """
        if not self.isVisible():
            return
        searchFlag = self.getUserSearchFlag()
        txt = self.ui.lineEditSearch.text()
        tc = self.editor.textEdit.textCursor()
        doc = self.editor.textEdit.document()
        tc.movePosition(QTextCursor.Start)
        cptMatches = 0
        tc = doc.find(txt, tc, searchFlag)
        while not tc.isNull():
            deco = self.createDecoration(tc)
            self._decorations.append(deco)
            self.editor.textEdit.addDecoration(deco)
            tc.setPosition(tc.position() + 1)
            tc = doc.find(txt, tc, searchFlag)
            cptMatches += 1
        self.numOccurrences = cptMatches

    def clearDecorations(self):
        """ Remove all decorations """
        for deco in self._decorations:
            self.editor.textEdit.removeDecoration(deco)
        self._decorations[:] = []

    def getUserSearchFlag(self):
        """ Returns the user search flag """
        searchFlag = 0
        if self.ui.checkBoxCase.isChecked():
            searchFlag |= QTextDocument.FindCaseSensitively
        if self.ui.checkBoxWholeWords.isChecked():
            searchFlag |= QTextDocument.FindWholeWords
        return searchFlag

    def highlightOccurrences(self, txt, selectFirst=False):
        """ Highlight occurences
        :param txt: Text to highlight
        :param selectFirst: True to select the first occurence
        """
        self._processing = True
        self.clearDecorations()
        self.highlightAllOccurrences()
        if selectFirst:
            self.selectFirst()
        self._processing = False
