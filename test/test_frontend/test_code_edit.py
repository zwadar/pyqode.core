"""
This module tests the CodeEdit class
"""
import mimetypes
import os
import platform

from PyQt4 import QtGui, QtCore
from PyQt4.QtTest import QTest

import pytest
from pyqode.core import frontend, style, settings
from pyqode.core.frontend import panels, modes
from ..helpers import cwd_at, wait_for_connected


app = None
editor = None
window = None


def process_events():
    global app
    app.processEvents()


@cwd_at('test')
def setup_module():
    """
    Setup a QApplication and CodeEdit which open the client module code
    """
    global app, editor, window
    app = QtGui.QApplication.instance()
    # import sys
    # app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()
    editor = frontend.CodeEdit(window)
    # frontend.install_mode(editor, modes.PygmentsSyntaxHighlighter(
    #     editor.document()))
    window.setCentralWidget(editor)
    window.resize(800, 600)
    window.show()
    frontend.start_server(editor, os.path.join(os.getcwd(), 'server.py'))
    wait_for_connected(editor)


def teardown_module():
    """
    Close server and exit QApplication
    """
    global editor, app
    frontend.stop_server(editor)
    app.exit(0)
    QTest.qWait(1000)
    del editor


def test_set_plain_text():
    global editor
    with pytest.raises(TypeError):
        editor.setPlainText('Some text')
    editor.setPlainText('Some text', mimetypes.guess_type('file.py')[0],
                        'utf-8')
    assert editor.toPlainText() == 'Some text'


def test_actions():
    # 13 default shortcuts
    nb_actions_expected = 13
    assert len(editor.actions()) == nb_actions_expected
    action = QtGui.QAction('my_action', editor)
    editor.add_action(action)
    nb_actions_expected += 1
    assert len(editor.actions()) == nb_actions_expected
    editor.add_separator()
    nb_actions_expected += 1
    assert len(editor.actions()) == nb_actions_expected


def test_duplicate_line():
    editor.setPlainText('Some text', mimetypes.guess_type('file.py')[0],
                        'utf-8')
    assert editor.toPlainText() == 'Some text'
    editor.duplicate_line()
    assert editor.toPlainText() == 'Some text\nSome text'


def test_show_tooltip():
    editor.show_tooltip(QtCore.QPoint(0, 0), 'A tooltip')


def test_margin_size():
    global editor, window
    # we really need to show the window here to get correct margin size.
    window.show()
    QTest.qWaitForWindowShown(window)
    for position in frontend.Panel.Position.iterable():
        # there is no panel on this widget, all margin must be 0
        assert editor.margin_size(position) == 0
    panel = frontend.panels.LineNumberPanel()
    frontend.install_panel(editor, panel,
                           position=frontend.Panel.Position.LEFT)
    panel.setVisible(True)
    process_events()
    # as the window is not visible, we need to refresh panels manually
    assert editor.margin_size(frontend.Panel.Position.LEFT) != 0
    window.hide()


def test_zoom():
    global editor
    assert editor.font_size == style.font_size
    editor.zoom_in()
    assert editor.font_size == style.font_size + 1
    editor.reset_zoom()
    assert editor.font_size == style.font_size
    editor.zoom_out()
    assert editor.font_size == style.font_size - 1

    while editor.font_size > 1:
        editor.zoom_out()
        if editor.font_size == 1:
            editor.zoom_out()
            assert editor.font_size == 1


def test_indent():
    editor.setPlainText('Some text', mimetypes.guess_type('file.py')[0],
                        'utf-8')
    frontend.goto_line(editor, 1)
    editor.indent()
    # no indenter mode -> indent should not do anything
    assert editor.toPlainText() == 'Some text'
    editor.un_indent()
    assert editor.toPlainText() == 'Some text'
    # add indenter mode, call to indent/un_indent should now work
    frontend.install_mode(editor, modes.IndenterMode())
    editor.setPlainText('Some text', mimetypes.guess_type('file.py')[0],
                        'utf-8')
    frontend.goto_line(editor, 1)
    editor.indent()
    assert editor.toPlainText() == '    Some text'
    editor.un_indent()
    assert editor.toPlainText() == 'Some text'


def test_whitespaces():
    assert not editor.show_whitespaces
    editor.show_whitespaces = True
    assert editor.show_whitespaces


def test_font_name():
    system = platform.system().lower()
    if system == 'linux':
        assert editor.font_name == 'monospace'
    elif system == 'windows':
        assert editor.font_name == 'Consolas'
    editor.font_name = 'deja vu sans'
    assert editor.font_name == 'deja vu sans'


def test_font_size():
    assert editor.font_size != 20
    editor.font_size = 20
    assert editor.font_size == 20


def test_foreground():
    assert editor.foreground.name() == QtGui.QColor("#000000").name()


def test_whitespaces_foreground():
    assert editor.whitespaces_foreground.name() == QtGui.QColor(
        "#d3d3d3").name()
    editor.whitespaces_foreground = QtGui.QColor("#FF0000")
    assert editor.whitespaces_foreground.name() == QtGui.QColor(
        "#FF0000").name()


def test_selection_background():
    assert editor.selection_background.name() == QtGui.QColor(
        "#4a90d9").name()
    editor.selection_background = QtGui.QColor("#FF0000")
    assert editor.selection_background.name() == QtGui.QColor(
        "#FF0000").name()


def test_selection_foreground():
    assert editor.selection_foreground.name() == QtGui.QColor(
        "#ffffff").name()
    editor.selection_foreground = QtGui.QColor("#FF0000")
    assert editor.selection_foreground.name() == QtGui.QColor(
        "#FF0000").name()


def test_file_attribs():
    editor.file_path = __file__
    assert editor.file_path == __file__
    assert editor.file_name == 'test_code_edit.py'


def test_setPlainText():
    editor.file_path = 'test.py'
    editor.setPlainText('', 'text/x-unknown', 'utf-8')


def test_delete():
    frontend.open_file(editor, __file__)
    txt = editor.toPlainText()
    frontend.select_lines(editor, 1, 1)
    editor.delete()
    assert txt != editor.toPlainText()


# def test_rehighlight():
#     global editor
#     editor.rehighlight()


def test_key_pressed_event():
    QTest.keyPress(editor, QtCore.Qt.Key_Tab)
    QTest.keyPress(editor, QtCore.Qt.Key_Backtab)
    QTest.keyPress(editor, QtCore.Qt.Key_Home)
    QTest.keyPress(editor, QtCore.Qt.Key_Return)


def test_key_released_event():
    QTest.keyRelease(editor, QtCore.Qt.Key_Tab)


def test_focus_out():
    frontend.open_file(editor, __file__)
    settings.save_on_focus_out = True
    editor.dirty = True
    assert editor.dirty is True
    editor.focusOutEvent(None)


def test_mouse_events():
    global editor
    QTest.mousePress(editor, QtCore.Qt.RightButton)
    QTest.mousePress(editor, QtCore.Qt.LeftButton, QtCore.Qt.ControlModifier,
                     QtCore.QPoint(200, 200))
    QTest.mouseRelease(editor, QtCore.Qt.RightButton)
    editor.mousePressEvent(QtGui.QMouseEvent(
        QtCore.QEvent.MouseButtonPress, QtCore.QPoint(10, 10),
        QtCore.Qt.RightButton, QtCore.Qt.RightButton, QtCore.Qt.NoModifier))
    editor.mouseReleaseEvent(QtGui.QMouseEvent(
        QtCore.QEvent.MouseButtonRelease, QtCore.QPoint(10, 10),
        QtCore.Qt.RightButton, QtCore.Qt.RightButton, QtCore.Qt.NoModifier))
    editor.wheelEvent(QtGui.QWheelEvent(
        QtCore.QPoint(10, 10), 1, QtCore.Qt.MidButton, QtCore.Qt.NoModifier))
    editor.mouseMoveEvent(QtGui.QMouseEvent(
        QtCore.QEvent.MouseMove, QtCore.QPoint(10, 10),
        QtCore.Qt.RightButton, QtCore.Qt.RightButton, QtCore.Qt.NoModifier))
    editor.verticalScrollBar().setValue(editor.verticalScrollBar().maximum())


def test_show_context_menu():
    global editor
    assert isinstance(editor, QtGui.QPlainTextEdit)
    editor.customContextMenuRequested.emit(QtCore.QPoint(10, 10))
    editor._mnu.hide()


def test_multiple_panels():
    editor.reset_zoom()

    p = panels.SearchAndReplacePanel()
    frontend.install_panel(editor, p, p.Position.BOTTOM)
    p.show()

    p = panels.LineNumberPanel()
    frontend.install_panel(editor, p)
    p.show()

    p = panels.MarkerPanel()
    frontend.install_panel(editor, p, p.Position.RIGHT)
    p.show()

    class SearchPanel(panels.SearchAndReplacePanel):
        pass

    p = SearchPanel()
    frontend.install_panel(editor, p, p.Position.TOP)
    p.show()

    editor.show()
    editor.refresh_panels()
    QTest.qWait(500)
    editor.hide()
    frontend.uninstall_all(editor)