'''
GuiConfig is a container class that acts like a dictionary of all the
control values in the given window and all children windows.  Pass to
__init__ the root window and optionally, 'items' (a dictionary) to
initialize the window values.

window values are generally accessed using the dictionary syntax, the key
being the name of the window.  If the window is not found, a KeyError will
be raised.
example:
g = GuiConfig(wx.Window())
g['text_control'] = 'Some text'
g['text_control'] # will return 'Some text'

Accessing the window values are also accessible using the attribute syntax.
If the window is not found, the default attribute path will be searched
example
g.text_control = 'Some text'
g.text_control # will return 'Some text'

GuiConfig can be either inherited by a class or used as a class attribute
(see the test for examples of both usages).  If used as one of multiple
inheritance, it is necessary that GuiConfig be the first child.  Oddly,
however, any wx.Window's should be initialized before GuiConfig.
example:
class DerivedClass(GuiConfig, wx.Frame):
  def __init__(self, parent):
    wx.Frame.__init__(self, parent, title="Testing a class derived from GuiConfig")
    GuiConfig.__init__(self, self, items={})

To access to the windows controls directly use the following syntax:
g.windows['text_control'] or g.windows.text_control
'''

import os
import traceback
import re
from collections import MutableMapping

from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader

try:
    import win32api
    import win32con
    bWin32 = True
except:
    bWin32 = False

os.environ["PYDRO_GUI"] = "qt"
from HSTB.shared import RegistryHelpers

qt_ext = "(_\d+)?$"  # optional trailing underscore with number (qt designer auto-names this way)
qt_automatic_window_names = {QtWidgets.QComboBox: re.compile("comboBox"+qt_ext),
    QtWidgets.QListWidget: re.compile("listWidget"+qt_ext),
QtWidgets.QLabel: re.compile("label"+qt_ext),
QtWidgets.QRadioButton: re.compile("radioButton"+qt_ext),
QtWidgets.QCheckBox: re.compile("checkBox"+qt_ext),
QtWidgets.QCalendarWidget: re.compile("calendarWidget"+qt_ext),
QtWidgets.QDateEdit: re.compile("dateEdit"+qt_ext),
QtWidgets.QTimeEdit: re.compile("timeEdit"+qt_ext),
QtWidgets.QDateTimeEdit: re.compile("dateTimeEdit"+qt_ext),
QtWidgets.QLineEdit: re.compile("lineEdit"+qt_ext),
QtWidgets.QPlainTextEdit: re.compile("plainTextEdit"+qt_ext),
QtWidgets.QTextEdit: re.compile("textEdit"+qt_ext),
QtWidgets.QSpinBox: re.compile("spinBox"+qt_ext),
QtWidgets.QDoubleSpinBox: re.compile("doubleSpinBox"+qt_ext),
QtWidgets.QProgressBar: re.compile("progressBar"+qt_ext),
QtWidgets.QDial: re.compile("dial"+qt_ext),
QtWidgets.QSlider: re.compile("((horizontal)|(vertical))Slider"+qt_ext),
              }


def getAllChildren(w, recurse):
    """For recurse returns the window being called, children, grandchildren etc.
    For recurse=False returns window.GetChildren() which won't include the window itself
    """
    if recurse:
        L = w.findChildren(QtWidgets.QWidget, QtCore.QRegExp(".*"))

        # L = [w]
        # try:
        #     if len(w.children()) > 0:
        #         for c in w.children():
        #             L += getAllChildren(c, recurse)
        # except AttributeError as e:
        #     # There is some bug/oddity in wxPython 3.0.2 where a ComboCtrl (and GenericDatePicker which uses it) doesn't return Children as wx objects but as SWIG Pointer and this makes the function fail.
        #     if "wxComboCtrl" in str(w):  # combo ctrls have transient children that popup but don't hold a value as such.  They should be ignored in (almost) all cases.
        #         pass
        #     else:
        #         raise e
    else:
        L = list(w.children())
    return L


class win_iter:
    def __init__(self, parent, recurse=True):
        self.children = getAllChildren(parent, recurse)
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.i += 1
        try:
            return self.children[self.i - 1]
        except IndexError:
            raise StopIteration


class win_dict(MutableMapping):
    '''When retrieving window instances can either call as dictionary or attribute:
    self.windows['plotScaleW']
    self.windows.plotScaleW
    '''

    def __init__(self, parent, recurse=True):
        self.parent = parent
        self.recurse = recurse

    def __iter__(self):
        return win_iter(self.parent, self.recurse)

    def __getitem__(self, name):
        for w in self.__iter__():
            if w.objectName() == name:
                return w
        raise KeyError("Object has no key '%s'" % str(name))

    def keys(self):
        for w in self.__iter__():
            yield w.objectName()

    def __getattr__(self, key):
        # Using the __getattr__ method is a little dangerous, if we're setting
        # this up as a derived class.  Be absolutely sure to raise a
        # AttributeError if it doesn't exist, otherwise the search will stop and
        # our sybling class(es) will not get searched for the attribute
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            try:
                return self.__getitem__(key)
            except KeyError:
                raise AttributeError("GuiConfig instance has no attribute '%s'" % str(key))

    def __delitem__(self, key):
        raise Exception("Can't delete windows like this")

    def __len__(self):
        return len(list(self.keys()))

    def __setitem__(self, key, val):
        raise Exception("unimplemented __setitem__ in win_dict")


class Manager(QtCore.QObject):
    """ A class to catch the close of the dialog/window and call the function
    to save the settings to the registry """

    def __init__(self, wnd, cb):
        super(Manager, self).__init__()
        self.w = wnd
        self.cb = cb
        self.w.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.w and event.type() == QtCore.QEvent.Close:
            self.quit_app()
            # event.ignore()
            # return True
        return super(Manager, self).eventFilter(obj, event)

    @QtCore.Slot()
    def quit_app(self):
        # some actions to perform before actually quitting:
        self.cb()
        self.w.removeEventFilter(self)


class GuiConfig:
    ''' If using the registry to save/load, it will autoload if the use_registry is supplied on __init__.
    Otherwise call UseRegistry and LoadFromRegistry.
    It will auto store if derived from a wx.frame but not wx.Dialog as the EVT_CLOSE doesn't seem to catch for dialogs.
    For a Dialog, call manually after an ShowModal() == ID_OK so that only saved when user is happy with the choices,
    discard when dialog is cancelled.

    Recurse defines if only children are searched or if all descendant windows (grandchildren etc) are considered.
    '''

    def __init__(self, root, items=None, use_registry='', recurse=True):
        self.root = root  # @todo there is a recursion problem occuring if root==self on the destruction of the root/self.
        if root is self:
            self.root = None
        self.recurse = recurse
        self.windows = win_dict(self.GetRoot(), recurse)  # self.__dict__['root'])
        if items:
            self.SetGUI(items)
        self.UseRegistry(use_registry)
        self.LoadFromRegistry()
        self.RestorePosition()
        self.q_catch_close = Manager(self.GetRoot(), self.OnCloseWin)
        # self.GetRoot().closeEvent = self.OnCloseWin
        # self.GetRoot().Bind(wx.EVT_CLOSE, self.OnCloseWin)

    def OnCloseWin(self, event=None):
        self.SaveToRegistry()

    def GetRoot(self):
        r = self.__dict__['root']
        if r is None:
            r = self
        return r

    def SetGUI(self, items, bIgnoreKeyErrors=True):
        for k, v in list(items.items()):
            try:
                self[k] = v
            except KeyError:
                if not bIgnoreKeyErrors:
                    print(traceback.print_exc())
                    raise KeyError

    def UseRegistry(self, key=''):
        self.reg_key = key

    def LoadFromRegistry(self):
        if self.reg_key:
            for name in self.keys():
                val = RegistryHelpers.GetDWORDFromRegistry(self.reg_key, name, None, bSilent=True)
                if val is None:
                    val = RegistryHelpers.GetPathFromRegistry(self.reg_key + '\\' + name, None, '')
                if val is not None:
                    self.__setitem__(name, val)

    def __setstate__(self, o):
        self.SetGUI(o)

    def __getstate__(self):
        return self.as_dict()

    def as_dict(self):
        return dict(self.named_items())

    def SaveToRegistry(self):
        '''
        Doesn't save things with default names as these could accidentally overwrite static items that are set by the constructor.
        '''
        if self.reg_key:
                # store everything that has a (potentially) unique name; avoid things with default name like wxSpinCtrl or staticText.
            self.SavePosition()
            for name, w in self.named_windows():
                try:
                    if isinstance(w, QtWidgets.QLabel):
                        continue  # don't save the value of static text
                    val = self.GetWindowValue(w)  # self.__getitem__(name) #using getitem is causing an n^2 problem as we are essentially calling iterwindows again for each window found.
                    if isinstance(val, int):
                        RegistryHelpers.SaveDWORDToRegistry(self.reg_key, name, val)
                    elif isinstance(val, (float)):
                        RegistryHelpers.SavePathToRegistry(self.reg_key + '\\' + name, str(val), '')
                    elif isinstance(val, (str)):
                        try:
                            RegistryHelpers.SavePathToRegistry(self.reg_key + '\\' + name, str(val), '')
                        except UnicodeEncodeError:
                            pass  # could be a label with a non-ascii character (like a degrees symbol)
                    else:
                        print('unknown window value type:', name, val, type(val))
                except AttributeError:
                    print('Attribute Error', name)

    def SavePosition(self):
        '''Old frame size/position save to registry, only used if the perspective save fails
        '''
        if bWin32 and self.reg_key:
            try:
                p = self.pos()
                rootwnd = self
            except:
                p = self.root.pos()
                rootwnd = self.root
            pos = (p.x(), p.y())
            name = self.reg_key + "\\MainFrame"
            try:
                if rootwnd.isMaximized():  # save that Pydro is maximized
                    RegistryHelpers.SaveDWORDToRegistry(name, "Max", 1)
                else:
                    RegistryHelpers.SaveDWORDToRegistry(name, "Max", 0)
            except:
                pass  # no all windows have a maximized attribute
            # find the max bounds of the screen (less twenty to make sure some of the window is visible, caption can be slightly off screen)
            if win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) != 0:
                minx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN) - 20
                miny = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN) - 20
                maxx = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) + minx
                maxy = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN) + miny
            else:  # not NT 5.0+ or win98+
                minx, miny = -20, -20
                maxx = win32api.GetSystemMetrics(win32con.SM_CXSCREEN) + minx
                maxy = win32api.GetSystemMetrics(win32con.SM_CYSCREEN) + miny
            if (pos[0] >= minx and pos[0] <= maxx) and (pos[1] >= miny and pos[1] <= maxy):   # Don't save if Pydro is minimized to Task Bar, or window is off screen
                try:
                    s = self.size()
                except:
                    s = self.root.size()
                size = (s.width(), s.height())
                RegistryHelpers.SaveDWORDToRegistry(name, "SizeX", size[0])
                RegistryHelpers.SaveDWORDToRegistry(name, "SizeY", size[1])
                RegistryHelpers.SaveDWORDToRegistry(name, "PosX", pos[0])
                RegistryHelpers.SaveDWORDToRegistry(name, "PosY", pos[1])

    def RestorePosition(self):
        '''Old frame size/position save to registry, only used if the perspective save fails
        '''
        if bWin32 and self.reg_key:
            name = self.reg_key + "\\MainFrame"
            wide = RegistryHelpers.GetDWORDFromRegistry(name, "SizeX", 700, bSilent=True)
            hi = RegistryHelpers.GetDWORDFromRegistry(name, "SizeY", 500, bSilent=True)
            x = RegistryHelpers.GetDWORDFromRegistry(name, "PosX", 0, bSilent=True)
            y = RegistryHelpers.GetDWORDFromRegistry(name, "PosY", 0, bSilent=True)
            maxsz = RegistryHelpers.GetDWORDFromRegistry(name, "Max", 0, bSilent=True)
            sz = QtCore.QSize(wide, hi)
            pt = QtCore.QPoint(x, y)
            # if wx.NOT_FOUND == wx.Display(0).GetFromPoint((x, y)):  # check that the upper left is on screen, otherwise move the window
            #     x, y = wx.Display(0).Geometry.GetTopLeft()
            try:
                self.adjustPosition(pt)
                self.resize(sz)
            except:
                self.root.move(pt)
                self.root.resize(sz)
            if maxsz:
                self.showMaximized()  # calling self.Maximize(max) causes weird screen flicker if max=false

    def iterwindows(self, w=None):
        return win_iter(self.GetRoot(), self.recurse)

    def keys(self):
        for w in self.iterwindows():
            try:
                yield w.objectName()
            except AttributeError:
                continue

    def values(self):
        for w in self.iterwindows():
            try:
                val = self.GetWindowValue(w)  # self.__getitem__(w.GetName()) #using getitem is causing an n^2 problem as we are essentially calling iterwindows again for each window found.
                yield val
            except AttributeError:
                continue

    def items(self):
        '''Return all the windows that have a get/set method available with it's current value.
           Won't return named windows that do not have a "value" accessible by __getitem__ '''
        for w in self.iterwindows():
            try:
                val = self.GetWindowValue(w)  # self.__getitem__(w.GetName()) #using getitem is causing an n^2 problem as we are essentially calling iterwindows again for each window found.
                yield w.objectName(), val
            except AttributeError:
                pass

    def named_items(self):
        items = []
        for name, w in self.named_windows():
            try:
                val = self.GetWindowValue(w)  # self.__getitem__(name) #using getitem is causing an n^2 problem as we are essentially calling iterwindows again for each window found.
                items.append((name, val))
            except AttributeError:
                continue
        return items

    def named_windows(self):
        '''returns a list of named windows that are not the standard names'''
        n = []
        for w in self.windows:  # store everything that has a (potentially) unique name; avoid things with default name like wxSpinCtrl or staticText.
            name = str(w.objectName())
            if name[:3].lower() == 'qt_':  #skip the qt_ named windows that are auto generated
                continue
            for wtype, searchstr in qt_automatic_window_names.items():
                if isinstance(w, wtype):
                    if not searchstr.match(name):
                        n.append((name, w))
                    else:
                        break  # found the type and had an auto-generated name

        return n

    def __len__(self):
        return len(list(self.keys()))

    def __contains__(self, item):
        return item in list(self.keys())

    def has_key(self, key):
        return key in list(self.keys())

    def __getitem__(self, key):
        '''Returns a value from the control that would be 'natural' like a boolean for a checkbox or a string for a text control.
        Raises an AttributeError if no value is found (window type not supported)
        '''
        try:
            # FindWindowByName can find itself, not just children.  So for parent name = child name this might return an unexpected window instance.
            # using self.windows will access a list created using the self.recurse flag which tells if we really want to search all windows or just the children
            w = self.windows[key]  # self.GetRoot().FindWindowByName(key)
        except:
            raise KeyError("GuiConfig instance has no key '%s'" % str(key))
        return self.GetWindowValue(w)

    def GetWindowValue(self, w):
        if isinstance(w, QtWidgets.QComboBox):  # This is a subclass of wx.Choice -- so check ComboBox and use GetValue first
            return w.currentText()
        elif isinstance(w, QtWidgets.QListWidget):
            return [i.text() for i in w.selectedItems()]
        elif isinstance(w, QtWidgets.QLabel):
            return w.text()
        elif isinstance(w, QtWidgets.QRadioButton):
            return w.isChecked()
        elif isinstance(w, QtWidgets.QCheckBox):
            if w.isTristate():  # note: tri-mode checkboxes eval to True if wx.CHK_CHECKED or wx.CHK_UNDETERMINED
                return w.checkState()  # wx.CHK_CHECKED,wx.CHK_UNCHECKED,wx.CHK_UNDETERMINED
            else:
                return w.isChecked()
        elif isinstance(w, QtWidgets.QCalendarWidget):
            return w.selectedDate().toPython()
        elif isinstance(w, QtWidgets.QDateEdit):
            return w.date().toPython()
        elif isinstance(w, QtWidgets.QTimeEdit):
            return w.time().toPython()
        elif isinstance(w, QtWidgets.QDateTimeEdit):
            return w.dateTime().toPython()
        elif isinstance(w, QtWidgets.QLineEdit):
            return w.text()
        elif isinstance(w, QtWidgets.QPlainTextEdit):
            return w.toPlainText()
        elif isinstance(w, QtWidgets.QTextEdit):  # should this use HTML?
            return w.toPlainText()
        elif isinstance(w, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            return w.value()
        elif isinstance(w, QtWidgets.QProgressBar):
            return w.value()
        elif isinstance(w, (QtWidgets.QDial, QtWidgets.QSlider)):
            return w.value()

        # we don't want w (ctrl) in general!; quasi-persistent GuiConfig ctrls are the exception rather than the rule (wx.Panel "hack" above); i.e., they become PyDeadObject
        # try:
        # print("unsupported type of Qt window '"+w.objectName()+"' "+str(type(w)))
        return w.text()
        # except AttributeError:
        #  if isinstance(w, wx.Panel): #The HSTP_DirBrowseButton control and the underlying wx control will return a GetValue in the "try" block.  This is for wx.Panel's that don't return a value
        #      print "returning the wx.Panel instance from gui config"
        #      raise Exception("tst")
        #      return w #we shouldn't be doing this, if the window instance is needed it should be gotten by the .windows.WinName syntax
        #  else:
        #      pass # e.g., for N/A button ctrls

    def __getattr__(self, key):
        # Using the __getattr__ method is a little dangerous, if we're setting
        # this up as a derived class.  Be absolutely sure to raise a
        # AttributeError if it doesn't exist, otherwise the search will stop and
        # our sybling class(es) will not get searched for the attribute
        if key in self.__dict__ or key == 'windows':  # avoid infinite loop when key==windows which is a special name for recursing the set of child windows
            return self.__dict__[key]
        else:
            if key[:2] == '__' and key[-2:] == '__':  # avoid trying to find windows named with Python builtins -- like __del__, __add__, __init__ etc.
                raise AttributeError("GuiConfig instance has no attribute '%s'" % str(key))
            # if key=='windows':
            #    return win_dict(self.GetRoot())#self.__dict__['root'])
            try:
                return self.__getitem__(key)
            except KeyError:
                raise AttributeError("GuiConfig instance has no attribute '%s'" % str(key))

    def __setitem__(self, key, value):
        try:
            w = self.windows[key]  # self.GetRoot().FindWindowByName(key)
        except:
            raise KeyError("GuiConfig instance has no key '%s'" % str(key))
        self.SetWindowValue(w, value)

    @staticmethod
    def SetWindowValue(w, value):
        if isinstance(w, QtWidgets.QComboBox):  # This is a subclass of wx.Choice -- so check ComboBox and use GetValue first
            if value is None:
                value = ""
            w.setCurrentText(value)
        elif isinstance(w, QtWidgets.QListWidget):
            w.clear()
            w.addItems(value)
        elif isinstance(w, QtWidgets.QLabel):
            try:
                if value is None:
                    value = ""
                w.setText(value)
            except:
                w.setText(str(value))
        elif isinstance(w, QtWidgets.QRadioButton):
            w.setChecked(value)
        elif isinstance(w, QtWidgets.QCheckBox):
            if w.isTristate():  # note: for tri-mode checkboxes, Set3StateValue(False)==Set3StateValue(wx.CHK_UNCHECKED)
                if isinstance(value, QtCore.Qt.CheckState):
                    # (QtCore.Qt.Unchecked, QtCore.Qt.PartiallyChecked, QtCore.Qt.Checked):
                    v = value
                else:
                    if value:
                        v = QtCore.Qt.Checked
                    else:
                        v = QtCore.Qt.Unchecked
                w.setCheckState(v)
            else:
                if value is None:
                    value = False
                w.setChecked(value)
        elif isinstance(w, (QtWidgets.QCalendarWidget, QtWidgets.QDateEdit)):
            if value is not None:
                try:
                    dt = QtCore.QDate(value)  # datetime objects
                except:  # ISO date string
                    dt = QtCore.QDate.fromString(value, "yyyy-MM-dd")
                if isinstance(w, QtWidgets.QCalendarWidget):
                    w.setSelectedDate(dt)
                else:
                    w.setDate(dt)
        elif isinstance(w, QtWidgets.QTimeEdit):
            if value is not None:
                try:
                    dt = QtCore.QTime(value)  # datetime objects
                except:  # ISO date string
                    dt = QtCore.QTime.fromString(value, "hh:mm:ss")
                w.setTime(dt)
        elif isinstance(w, QtWidgets.QDateTimeEdit):
            if value is not None:
                try:
                    dt = QtCore.QDateTime(value)  # datetime objects
                except:  # ISO date string
                    dt = QtCore.QDateTime.fromString(value, "yyyy-MM-dd hh:mm:ss")
                w.setDateTime(dt)
        elif isinstance(w, QtWidgets.QLineEdit):
            w.setText(value)
        elif isinstance(w, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            w.setValue(float(value))
        elif isinstance(w, QtWidgets.QProgressBar):
            w.setValue(value)
        elif isinstance(w, (QtWidgets.QDial, QtWidgets.QSlider)):
            w.setValue(value)
        elif isinstance(w, QtWidgets.QPlainTextEdit):
            return w.setPlainText(value)
        elif isinstance(w, QtWidgets.QTextEdit):  # should this use HTML?
            return w.setPlainText(value)

        else:
            # traceback.print_exc()
            print("Error while trying to setitem in GuiConfig:")
            print(w.objectName(), value)  # this shouldn't be too silent -- it's really a bug that needs to be found if it gets here.

    def __setattr__(self, key, value):
        try:
            return GuiConfig.__setitem__(self, key, value)

        # If we don't have a window named key, then create a new attribute directly
        except KeyError:
            self.__dict__[key] = value
            return value

    def __str__(self):
        L = ["'%s': %s" % (k, v) for k, v in list(self.items())]
        return '{' + ', '.join(L) + '}'


class guiconfig_mixin:
    def __init__(self, ui_file_path, custom_widgets=[], **kwrds):
        ui_file = QtCore.QFile(ui_file_path)
        ui_file.open(QtCore.QFile.ReadOnly)

        loader = QUiLoader()
        for cw in custom_widgets:
            loader.registerCustomWidget(cw)
        self.win = loader.load(ui_file)
        self.gui = GuiConfig(self.win, **kwrds)
