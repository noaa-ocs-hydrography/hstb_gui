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

import traceback
import re
from collections import MutableMapping

import wx
from wx.adv import CalendarCtrl, GenericDatePickerCtrl

try:
    import win32api
    import win32con
    bWin32 = True
except:
    bWin32 = False

from HSTB.shared import RegistryHelpers


def getAllChildren(w, recurse):
    '''For recurse returns the window being called, children, grandchildren etc.
    For recurse=False returns window.GetChildren() which won't include the window itself
    '''
    if recurse:
        L = [w]
        try:
            if len(w.GetChildren()) > 0:
                for c in w.GetChildren():
                    L += getAllChildren(c, recurse)
        except AttributeError as e:
            # There is some bug/oddity in wxPython 3.0.2 where a ComboCtrl (and GenericDatePicker which uses it) doesn't return Children as wx objects but as SWIG Pointer and this makes the function fail.
            if "wxComboCtrl" in str(w):  # combo ctrls have transient children that popup but don't hold a value as such.  They should be ignored in (almost) all cases.
                pass
            else:
                raise e
    else:
        L = list(w.GetChildren())  # converts from wxWindowList to standard python list -- FWIW
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
            if w.GetName() == name:
                return w
        raise KeyError("Object has no key '%s'" % str(name))

    def keys(self):
        for w in self.__iter__():
            yield w.GetName()

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
        self.GetRoot().Bind(wx.EVT_CLOSE, self.OnCloseWin)
#    try:
#        self.rootDestroy = root.Destroy #cache and catch the Destroy function for a window
#        root.Destroy = self.GuiDestroy
#    except:
#        pass #no Destroy method
#    try:
#        self.rootClose = root.Close #cache and catch the Destroy function for a window
#        root.Close = self.GuiClose
#    except:
#        pass #no Destroy method
#  def GuiClose(self, *args):
#      print 'Destroying wingow -- guiconfig save!'
#      self.SaveToRegistry()
#      self.rootClose(*args)
#  def GuiDestroy(self, *args):
#      print 'Destroying wingow -- guiconfig save!'
#      self.SaveToRegistry()
#      self.rootDestroy(*args)

#  def __del__(self):
#      del self.windows

    def OnCloseWin(self, event):
        self.SaveToRegistry()
        event.Skip()

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
            for name, w in self.named_windows():
                try:
                    val = self.GetWindowValue(w)  # self.__getitem__(name) #using getitem is causing an n^2 problem as we are essentially calling iterwindows again for each window found.
                    if isinstance(val, int):
                        RegistryHelpers.SaveDWORDToRegistry(self.reg_key, name, val)
                    elif isinstance(val, (str)):
                        try:
                            RegistryHelpers.SavePathToRegistry(self.reg_key + '\\' + name, str(val), '')
                        except UnicodeEncodeError:
                            pass  # could be a label with a non-ascii character (like a degrees symbol)
                    else:
                        print('unknown window value type:', name, val, type(val))
                except AttributeError:
                    print('Attribute Error', name)
            self.SavePosition()

    def SavePosition(self):
        '''Old frame size/position save to registry, only used if the perspective save fails
        '''
        if bWin32 and self.reg_key:
            try:
                pos = self.GetPosition()
                rootwnd = self
            except:
                pos = self.root.GetPosition()
                rootwnd = self.root
            name = self.reg_key + "\\MainFrame"
            try:
                if rootwnd.IsMaximized():  # save that Pydro is maximized
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
                    size = self.GetSize()
                except:
                    size = self.root.GetSize()
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
            if wx.NOT_FOUND == wx.Display(0).GetFromPoint((x, y)):  # check that the upper left is on screen, otherwise move the window
                x, y = wx.Display(0).Geometry.GetTopLeft()
            try:
                self.SetSize(x, y, wide, hi)
            except:
                self.root.SetSize(x, y, wide, hi)
            if maxsz:
                self.Maximize(True)  # calling self.Maximize(max) causes weird screen flicker if max=false

    def iterwindows(self, w=None):
        return win_iter(self.GetRoot(), self.recurse)

    def keys(self):
        for w in self.iterwindows():
            try:
                yield w.GetName()
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
                yield w.GetName(), val
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
            name = str(w.GetName())
            s = 2 if name[:2].lower() == 'wx' else 0
            if len(name.lower()[s:]) < 3 or name.lower()[s:] not in str(type(w)).lower():
                # StaticBox instances are named "groupBox", so add a handler for that
                if not (isinstance(w, wx.StaticBox) and name.lower() == "groupbox"):
                    n.append((name, w))
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
        if isinstance(w, wx.ComboBox):  # This is a subclass of wx.Choice -- so check ComboBox and use GetValue first
            return w.GetValue()
        elif isinstance(w, wx.CheckListBox):
            return w.GetCheckedStrings()
        elif isinstance(w, (wx.RadioBox, wx.Choice)):
            return w.GetStringSelection()
        elif isinstance(w, wx.StaticText):
            return w.GetLabel()
        elif isinstance(w, wx.CheckBox):
            if w.Is3State():  # note: tri-mode checkboxes eval to True if wx.CHK_CHECKED or wx.CHK_UNDETERMINED
                return w.Get3StateValue()  # wx.CHK_CHECKED,wx.CHK_UNCHECKED,wx.CHK_UNDETERMINED
            else:
                return w.GetValue()
        elif isinstance(w, GenericDatePickerCtrl):
            dte = w.GetValue()
            if dte.IsValid():
                return dte.FormatISODate()
            else:
                return None
        elif isinstance(w, CalendarCtrl):
            return w.GetDate().FormatISODate()
        # we don't want w (ctrl) in general!; quasi-persistent GuiConfig ctrls are the exception rather than the rule (wx.Panel "hack" above); i.e., they become PyDeadObject
        # try:
        return w.GetValue()
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
        if isinstance(w, wx.ComboBox):  # This is a subclass of wx.Choice -- so check ComboBox and use GetValue first
            if value is None:
                value = ""
            w.SetValue(value)
        elif isinstance(w, wx.CheckListBox):
            if value is None:
                value = ""
            w.SetCheckedStrings(value)
        elif isinstance(w, (wx.RadioBox, wx.Choice)):
            if value is not None:
                w.SetStringSelection(value)
        elif isinstance(w, wx.StaticText):
            try:
                if value is None:
                    value = ""
                w.SetLabel(value)
            except:
                w.SetLabel(str(value))
        elif isinstance(w, wx.CheckBox):
            if w.Is3State():  # note: for tri-mode checkboxes, Set3StateValue(False)==Set3StateValue(wx.CHK_UNCHECKED)
                if value is None:
                    value = wx.CHK_UNCHECKED
                w.Set3StateValue(value)  # wx.CHK_CHECKED,wx.CHK_UNCHECKED,wx.CHK_UNDETERMINED
            else:
                if value is None:
                    value = False
                w.SetValue(value)
        elif isinstance(w, (CalendarCtrl, GenericDatePickerCtrl)):
            if value is not None:
                if not isinstance(value, (str)):  # datetime object?
                    value = value.isoformat()
                # code from s100py.s1xx for decent iso parsing, better than python 3.7 builtin  function too.
                re_date = r"(?P<year>\d{4})[-]?(?P<month>\d{2})[-]?(?P<day>\d{2})"
                re_time = r"(?P<hour>\d{2})[: -]?(?P<minute>\d{2})[:-]?(?P<second>\d{2})(?P<decimal_sec>\.\d+)?"
                re_timezone = r"(?P<tz>(Z|(?P<tz_hr>[+-]\d{2})[:]?(?P<tz_min>\d{2})?))?"
                re_time_with_zone = re_time + re_timezone
                re_full_datetime = re_date + "T?" + re_time_with_zone
                re_date_optional_time = re_date + "T?(" + re_time_with_zone + ")?"
                match = re.match(re_date_optional_time, value).groupdict()
                # if match:
                #     decimal_sec = int(float(match['decimal_sec']) * 1000000) if match['decimal_sec'] else 0
                #     val = datetime.datetime(int(match['year']), int(match['month']), int(match['day']),
                #                             int(match['hour']), int(match['minute']), int(match['second']),
                #                             decimal_sec, tzinfo=zone)

                if isinstance(w, wx.calendar.CalendarCtrl):
                    try:  # bug in Calendar control is not refreshing the month dropdown box (when year is different but month was same) jitter the month to make th display refresh
                        w.SetDate(wx.DateTimeFromDMY(int(match['day']), int(match['month']) - 2, int(match['year'])))
                    except:
                        pass
                    try:
                        w.SetDate(wx.DateTimeFromDMY(int(match['day']), int(match['month']), int(match['year'])))
                    except:
                        pass
                    w.SetDate(wx.DateTimeFromDMY(int(match['day']), int(match['month']) - 1, int(match['year'])))
                else:
                    w.SetValue(wx.DateTimeFromDMY(int(match['day']), int(match['month']) - 1, int(match['year'])))
            else:  # Trying to re-initialize the control
                if isinstance(w, GenericDatePickerCtrl):
                    w.SetValue(wx.DateTime())  # send an invalid time object which clears the control
                else:
                    w.SetDate()  # @todo this will probably raise an exception -- need to fix
        else:
            try:
                try:
                    w.SetValue(value)
                except (TypeError, ValueError):  # IntCtrl raises a ValueError if a long is passed in (like 1L )
                    try:
                        uv = "" if value is None else str(value)
                        w.SetValue(uv)  # most controls like strings, in case user sent an integer etc.
                    except (TypeError, ValueError):
                        # traceback.print_exc()
                        uv = 0 if value is None else int(value)
                        w.SetValue(int(value))  # spin controls want integers, perhaps we have a string here
            except:  # catch all; including PyDeadObject bugfix
                # traceback.print_exc()
                print("Error while trying to setitem in GuiConfig:")
                print(w.GetName(), value)  # this shouldn't be too silent -- it's really a bug that needs to be found if it gets here.

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


if __name__ == '__main__':

    print("Running a test of the GuiConfig class")

    class testFrame(wx.Frame):
        def __init__(self, parent, **kwargs):
            wx.Frame.__init__(self, parent, **kwargs)

            item0 = wx.BoxSizer(wx.VERTICAL)
            item1 = wx.StaticText(self, -1, "A text label", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
            item1.SetName("static_text")
            item0.Add(item1)
            item2 = wx.TextCtrl(self, -1, "none", wx.DefaultPosition, wx.DefaultSize)
            item2.SetName("text_ctrl")
            self.panel = wx.Panel(self, -1, size=wx.Size(300, 50))  # put InsertAs radiobox on wx.Panel that's a child of frame; otherwise, wx.EVT_RADIOBOX doesn't work
            self.rb = item3 = wx.RadioBox(self.panel, -1, "Datum", wx.DefaultPosition, wx.DefaultSize,
                                          ["MLLW", "MSL", "MHW", "STND", "NGVD", "NAVD", "IGLD"], 1, wx.RA_SPECIFY_COLS)
            item3.SetName("soap_datum")
            self.Bind(wx.EVT_RADIOBOX, self.OnChangeRadio, id=self.rb.GetId())
            item4 = wx.TextCtrl(self, -1, "none", size=[320, 20])
            item4.SetName("another_text")
            item5 = wx.Button(self, -1, "test", wx.DefaultPosition, wx.DefaultSize, 0)
            self.button_id = item5.GetId()
            item0.Add(item2)
            item0.Add(self.panel)
            item0.Add(item4)
            item0.Add(item5)

            self.sizer = item0
            self.sizer.SetSizeHints(self)
            self.sizer.Layout()
            self.Bind(wx.EVT_BUTTON, self.OnButton, id=self.button_id)
            self.Show()

        def OnChangeRadio(self, event):
            event.Skip()
            print(self.rb.GetSelection())

        def OnButton(self, event):
            print(self.rb.GetSelection())

    app = wx.App()

    print("Creating a frame who has a class attribute which is a GuiConfig object")
    frame = testFrame(None, title="Testing where a GuiConfig object is a class attribute")

    print("  Setting properties via GuiConfig.__setattr__ and GuiConfig.__setitem__ interfaces")

    frame.g = GuiConfig(frame, items={'another_text': 'This text control was set at GuiConfig init time'})

    frame.g['text_ctrl'] = 'Text'
    frame.g.text_ctrl = 'Other Text'
    frame.g.soap_datum = 'STND'
    frame.g['soap_datum'] = 'MHW'

    print("  Asserting that all properties were properly set")

    assert(frame.g.soap_datum == 'MHW')
    assert(frame.g['soap_datum'] == 'MHW')
    assert(frame.g.text_ctrl == 'Other Text')
    assert(frame.g['text_ctrl'] == 'Other Text')
    print('hello')
    frame.g.UseRegistry('TestGuiConfig')
    frame.g.LoadFromRegistry()

    print("  Assertions passed")

    class DerivedClass(GuiConfig, testFrame):
        def __init__(self, parent):
            # The wx.Frame.__init__ must be called FIRST, to be able to initialize the windows
            testFrame.__init__(self, parent, title="Testing a class derived from GuiConfig")
            GuiConfig.__init__(self, self, items={'another_text': 'This text control was set at GuiConfig init time'}, use_registry='TestDerivedGuiConfig')
            # Make sure that we can still set attributes and they'll be OK
            self.attr1 = "An Attribute"
            self.attr2 = "Another attribute"
            # This should raise an exception
            try:
                print("  Trying to set a non-existent window")
                self['does_not_exist']
            except KeyError:
                print("  Good.  A KeyError was raised which is exactly what we want")
            # print 'opening', self.soap_datum
            # self.soap_datum = 'IGLD'
            # print 'opening2', self, self.soap_datum

    print("\nCreating a frame which is derived from GuiConfig")
    other_frame = DerivedClass(None)

    print("  Setting properties via GuiConfig.__setattr__ and GuiConfig.__setitem__ interfaces")

    if 1:
        other_frame['text_ctrl'] = 'Text'
        other_frame.text_ctrl = 'Other Text'
        other_frame.soap_datum = 'STND'
        other_frame['soap_datum'] = 'MHW'

        print("  Asserting that all properties were properly set")

        assert(other_frame.soap_datum == 'MHW')
        assert(other_frame['soap_datum'] == 'MHW')
        assert(other_frame.text_ctrl == 'Other Text')
        assert(other_frame['text_ctrl'] == 'Other Text')
        assert(other_frame.windows['text_ctrl'].GetValue() == 'Other Text')
        assert(other_frame.attr2 == "Another attribute")
    # other_frame.LoadFromRegistry()
    print("  Assertions passed")

    print("It seems that all the tests have gone smoothly.  Double check the test by visually inspecting that both windows are the same.  If they are, you may close down this windows at any time and have a little more confidence in the GuiConfig class.")

    app.MainLoop()
