
import os
import tempfile
import re

import win32api
import win32con
import win32help
import wx
import wx.py  # import shell, filling
from wx import aui
import importlib
try:
    from wx import TaskBarIcon, EVT_TASKBAR_LEFT_DCLICK, EVT_TASKBAR_RIGHT_UP
    from wx import SplashScreen, SPLASH_CENTRE_ON_SCREEN, SPLASH_TIMEOUT
    from wx import ST_SIZEGRIP as STB_SIZEGRIP
except ImportError:
    from wx.adv import TaskBarIcon, EVT_TASKBAR_LEFT_DCLICK, EVT_TASKBAR_RIGHT_UP
    from wx.adv import SplashScreen, SPLASH_CENTRE_ON_SCREEN, SPLASH_TIMEOUT
    from wx import STB_SIZEGRIP
#    from wx.lib.agw import aui

PathToApp = os.getcwd() + "\\"

from HSTB.shared.RegistryHelpers import *
from HSTB.shared import Constants
from HSTB.resources import PathToResource
from HSTB.gui import About

_dHSTP = Constants.UseDebug()  # Control debug stuff (=0 to hide debug menu et al from users in the field)


class ShellWindow(wx.py.shell.Shell):

    def __init__(self, parent, addlocals={}, introtext=""):
        self.parent = parent
        aliases = {'self': self,
                   'parent': self.parent,
                   }
        aliases.update(addlocals)
        varlist = "Locals:  "
        kys = list(aliases.keys())
        kys.sort()
        for k in kys:
            varlist += k + "  "
        wx.py.shell.Shell.__init__(self, parent, -1, introText="\n".join([varlist, introtext]), locals=aliases)
        # self.AddFilling()

    def AddFilling(self):
        self.filling = wx.py.filling.Filling(self.parent, -1, rootObject=self.interp.locals, rootIsNamespace=1)

    def Test(self):
        pass


class SelfClearingTextCtrl(wx.TextCtrl):

    def __init__(self, parent, id=-1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, limitlines=250, limitchar=20000):
        wx.TextCtrl.__init__(self, parent, id, style=style)
        self.limitlines = limitlines
        self.limitchar = limitchar
        self.tmpfile = tempfile.TemporaryFile()  # automatically destroyed when object is closed

    def NewLog(self):
        self.tmpfile = tempfile.TemporaryFile()  # automatically destroyed when object is closed

    def WriteText(self, txt, bArchive=0):
        if self.GetNumberOfLines() > self.limitlines or self.GetLastPosition() > self.limitchar:
            self.Clear()
        wx.TextCtrl.WriteText(self, txt)
        if bArchive or _dHSTP:  # archive at time of write - leads to more natural display and doesn't store fluff messages by default
            self.tmpfile.write(txt)
            self.tmpfile.flush()

    def Clear(self):
        # store the text to the temp file
        # for n in range(self.GetNumberOfLines()):
        #    self.tmpfile.write(self.GetLineText(n)+"\n")
        # self.tmpfile.flush()
        wx.TextCtrl.Clear(self)  # clear the display

    def AppendToFile(self, filepath):
        # self.Clear() #update with current text (and flushes buffer)
        origfile = open(filepath, "ab+")
        self.tmpfile.seek(0)
        try:
            while True:
                origfile.write(next(self.tmpfile.file))
        except StopIteration:
            pass  # eof
        self.NewLog()


class ZoomelatorSplitter(wx.SplitterWindow):

    def __init__(self, parent, ID, style=0x0100 | 0x0400):
        # default style is wx.SP_3DSASH | wx.SP_FULLSASH which isn't exported by wx.Python
        wx.SplitterWindow.__init__(self, parent, ID, style=style)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroyWindow)
        # Don't know why this version doesn't work
        #wx.EVT_COMMAND(self, self.GetId(), wx.wxEVT_DESTROY, self.OnDestroyWindow)

        #wx.EVT_SPLITTER_SASH_POS_CHANGED(self, self.GetId(), self.OnSashChanged)
        # replaced the sash position changed with equivalent command - for instructive reasons
        self.Bind(wx.EVT_COMMAND, self.GetId(), wx.wxEVT_COMMAND_SPLITTER_SASH_POS_CHANGED, self.OnSashChanged)
        self.Bind(wx.EVT_COMMAND, self.GetId(), wx.wxEVT_COMMAND_SPLITTER_SASH_POS_CHANGING, self.OnSashChanging)

        # Paint event should be useful elsewhere
        #wx.EVT_COMMAND(self, self.GetId(), wx.wxEVT_PAINT, self.OnDestroyWindow)
        self.log = None
        self.parent = parent
        self.childToShareWith = None

    def SetLog(self, log):
        self.log = log

    def ShareWith(self, child):
        """ Specify a child splitter that should get resized by an amount opposite of the parent
        to give the illusion of not moving """
        self.childToShareWith = child

    def OnSashChanged(self, evt):
        if self.log != None:
            self.log.WriteText("sash changed to %s\n" % str(evt.GetSashPosition()))
        if self.childToShareWith:
            childPos = self.childToShareWith.GetSashPosition()
            # bug in wx.Windows that causes the Sash to change to its new position before this function
            # so that delta is always zero and you cannot veto the change.  Added a "changing" handler to compensate
            deltaPos = self.oldPos - evt.GetSashPosition()  # self.GetSashPosition()
            self.childToShareWith.SetSashPosition(childPos + deltaPos)
        self.Refresh()

    def OnSashChanging(self, evt):
        if self.childToShareWith:
            self.oldPos = self.GetSashPosition()

    def SaveSashPos(self):
        if self.log != None:
            self.log.WriteText("SavedSashPos SOFTWARE\\Tranya\\" + self.GetName())
        SaveDWORDToRegistry(self.GetName(), "SashPos", self.GetSashPosition())

    def RestoreSashPos(self, default=100):
        pos = GetDWORDFromRegistry(self.GetName(), "SashPos", default)
        self.SetSashPosition(pos)
        return pos

    def OnDestroyWindow(self, evnt):
        self.SaveSashPos()
        evnt.Skip()

# Given a function OnOpen for a frame and you want to change it's code while running and use reload
# def OnOpen(self, event):
#    GetDirectory("Choose Directory")
# def OnOpen(self, event):
#    GetFile("Choose File")
# At some point we have to tie the menu item name and id to the function to be called
#wx.EVT_MENU(self, ID, self.OnOpen)
#
# Rather than creating the menus by hand we'll make a convention to pass in the menus/functions and will create the menu items, ids etc.
# Menu creation choices:
#        1) ("Open", self.OnOpen)  :  This won't work after a reload and will call the old bytecode and run the GetDirectory
#        2) ("Open") : Have all the events funneled to one PROCESSING function that reads the event name and reacts accordingly
#            This does reload well if the PROCESSING function call other functions, but any code within it won't reload
#            def PROCESSING(event):
#                if event.name == 'Open':
#                    os.chdir("c:\\temp")
#                    self.OnOpen(event) #calls the new OnOpen but if you modified the function name here or other code, like c:\temp to c:\user\temporary
#                    # those changes wouldn't be seen
#            Also this causes redundant places that "Open" must be added/changed and extra checking of the event name
#            Not pythonic but functional.
#        3) ("Open", 'self.OnOpen', -1) : would do an eval in the creation routine, but self and other objects won't come across properly
#            They'd have to be eval'd before passing to the creation routine, extra code required by the derived user class
#        4) ("Open", self, 'OnOpen', -1) : This works by doing an __getattribute__ call in the base class.
#            The object (self or module name) would be preserved so no burden on the caller though the syntax is slightly messier
#            On reload of class doing an Update of the menu (basically re-binding using the original stored IDs and the same __getattr__)
#            Update: modified menu creation to auto-generate the functionname if not supplied so ("Open", self) is sufficient.
#        5) )("Open", OnOpen) : This would be a class attribute (note the lack of use of self) but would not allow the storage of menuIDs as they'd be wiped out on reload
#            This would require the storage of a separate EventID cache that could be matched up later.
#            This again would place some burden on the user class and also creates a naming restriction if a dictionary is used to store menuIDs
#            If a dictionary wasn't used then there may be a mixup if the menu layout changed but the menuIDs don't follow
#            Also would have to use functools.partial or else this would be an unbound method, again a user burden
# Pydro is using #2 but I think should switch to #4, 500 lines of code (15% of Pydro.py) are spent in the PROCESS function


class HSTPMenuGroup(list):

    def __init__(self, menutxt, submenu=[], id=-1):
        '''initializes a list --
        ['MenuText', [ [menu items_1], [menu items_2]...], MenuID]
        '''
        list.__init__(self, [menutxt, submenu, id])

    def GetText(self):
        return self[0]

    def GetID(self):
        return self[2]

    def SetID(self, v):
        self[2] = v

    def GetSubItems(self):
        return self[1]

    def SetSubItems(self, v):
        self[1] = v

    def InsertSection(self, n, s):
        self[1].insert(n, s)

    def RemoveSubItems(self):
        self[1] = []

    def AppendSection(self, s):
        self[1].append(s)

    def AppendItem(self, i):
        try:
            self[1][-1].append(i)
        except:
            self[1].append([i])

    def copy(self):
        return HSTPMenuGroup(self[:])


class HSTPMenuItem(list):

    def __init__(self, menutxt, obj, method_str='', id=-1, exists=False):
        '''initializes a list --
        ['MenuText', object_to_call, FunctionName_string, MenuID]
        If method_str is not specified it is built from the menutxt
          by removing the spaces, "&" and "/" and prepending "On"
          So "&Func Txt" becomes OnFuncTxt
        Functions are called using obj.__getattribute__(method_str) and
          bound to the MENU_EVT with ID = id (which is created if -1 is specified)
        '''
        if not method_str:
            s = menutxt
            v = re.search('\&?[\w  /]*', s).group()
            method_str = 'On' + v.replace('&', '').replace(' ', '').replace('/', '')
        list.__init__(self, [menutxt, obj, method_str, id, exists])

    def GetID(self):
        return self[3]

    def SetID(self, v):
        self[3] = v

    def GetText(self):
        return self[0]

    def GetObj(self):
        return self[1]

    def GetMethodName(self):
        return self[2]

    def Exists(self):
        return self[4]

    def SetExists(self, v=True):
        self[4] = v


class HSTP_AUI_Frame(wx.Frame):

    def __init__(self, parent, id, title, RegistryAppName, InternalEvents, Menus, _Zevents, DisabledMenus=[], newMenus=[]):
        '''Menus should be laid out as following: @TODO -- change to ordered dictionary in a future version of python
        [[MenuName,[MenuItem, MenuItem]], [SecondMenuName, [MenuItem, MenuItem]]]
        A MenuItem can either be [ItemName, object, attribute, menu_id]
            object would be the class instance or a modulename,
            attribute is the function to call from the event handler
            menu_id should be specified as -1 and will be filled by the generated menu_id
            This eventually creates the following call
            wx.EVT_MENU(self, menu_id, object.__getattribute__(attribute))
            [['File,['Open', self, 'OnFileOpen', -1]], ['Window',['Preferences', self, 'OnPref',-1]]] would be an example

        '''
        wx.Frame.__init__(self, parent, -1, title, size=(800, 600),
                          style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        # tell FrameManager to manage this frame
        self._mgr = aui.AuiManager()
        try:
            self._mgr.SetFlags(aui.AUI_MGR_DEFAULT | aui.AUI_MGR_ALLOW_ACTIVE_PANE)
        except AttributeError:
            pass
        self._mgr.SetManagedWindow(self)

        # self.help_handle = win32help.HtmlHelp(0, None, win32help.HH_INITIALIZE)[1]

        self.appname = RegistryAppName
        self.SetTips(None)  # apps should set as appropriate after instantiating a MainFrame object

        # default windows behaviour is for child frames to always be on top of parent - to overcome this use None as parent and
        # list frames here that are parented to desktop so that they can be overlapped by parent
        self.CreateZTaskBar()
        if newMenus:
            G = HSTPMenuGroup
            I = HSTPMenuItem
            self.help_menu = G('&Help', [
                [
                    I('Show Tip', self, 'ShowTip', -1),
                    I('&HSTP Help', self, 'ShowHelp', -1),
                    I('Online Pydro Docs', self, 'OnDocsWebsite', -1),
                    I('Online Support', self, 'OnDocsWebsite', -1),
                    I('Email Support', self, 'EmailHelpRequest'),
                    I('Turn On AutoUpdate at Startup', self, 'AutoUpdateOn'),
                    I('Turn Off AutoUpdate at Startup', self, 'AutoUpdateOff'),
                    #I('Change Log', self, '', -1),
                    #I('Upcoming Changes', self, 'OnFutureChangeLog', -1),
                    I('&About\tCtrl-H', self, 'OnHelpAbout', -1),
                ]
            ]
            )
            if Constants.UseDebug():  # Control debug stuff (=0 to hide debug menu et al from users in the field)
                self.help_menu.AppendItem(I('&PeekXTF Help', self, 'ShowPeekHelp', -1))
                self.help_menu.AppendItem(I('&MidTierPeek Help', self, 'ShowMTPHelp', -1))
                self.help_menu.AppendItem(I('&Show/Hide Shell', self))
                self.help_menu.AppendItem(I('&Show Widget Inspector', self))

            self.CreateNewMenuBar(InternalEvents, newMenus, DisabledMenus)
        else:
            self.CreateZMenuBar(InternalEvents, Menus, _Zevents, DisabledMenus)
        self.CreateZToolBar()
        self.CreateZStatusBar()

        self.CreateZFrameLayout()
        self.default_persp = PathToApp + self.appname + '.default.psl'
        try:
            self.LoadPerspective(self.default_persp)
        except:
            self.RestorePos()

        # Some generic handler declarations for ZoomelatorFrame
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        # Show How To Use The Closing Panes Event
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)

    def OnPaneClose(self, event):
        event.Skip()

    def SetTips(self, relpath):
        self.TipFilename = relpath

    def SetStatusbarWidths(self, lst):
        nfields = len(lst)
        # change later
        if nfields < 2:   # must have a least 2 fields for gradient progress controls
            nfields = 2
            self.sbar.SetFieldsCount(2)   # default field widths [-1,-1]
        else:
            self.sbar.SetFieldsCount(nfields)
            self.sbar.SetStatusWidths(lst)
        self.sbarFields = nfields

    def AutoUpdateOn(self, event=None):
        SaveDWORDToRegistry("Pydro\\Preferences", "AutoUpdate", 1)

    def AutoUpdateOff(self, event=None):
        SaveDWORDToRegistry("Pydro\\Preferences", "AutoUpdate", 0)

    def EmailHelpRequest(self, event=None):
        strAddress = 'mailto:jack.riley@noaa.gov,barry.gallagher@noaa.gov?&subject=Pydro Question (v%s) &body=' % Constants.PydroVersion()
        strBody = 'RevNumber:' + Constants.PydroMinorVersion() + 'OS version:' + str(win32api.GetVersionEx())
        win32api.ShellExecute(0, 'open', strAddress + strBody, None, "", 1)

    def SavePos(self):
        '''Old frame size/position save to registry, only used if the perspective save fails
        '''
        pos = self.GetPositionTuple()
        name = self.appname + "\\MainFrame"
        if self.IsMaximized():  # save that Pydro is maximized
            SaveDWORDToRegistry(name, "Max", 1)
        else:
            SaveDWORDToRegistry(name, "Max", 0)
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
            size = self.GetSizeTuple()
            SaveDWORDToRegistry(name, "SizeX", size[0])
            SaveDWORDToRegistry(name, "SizeY", size[1])
            SaveDWORDToRegistry(name, "PosX", pos[0])
            SaveDWORDToRegistry(name, "PosY", pos[1])

    def RestorePos(self):
        '''Old frame size/position save to registry, only used if the perspective save fails
        '''
        name = self.appname + "\\MainFrame"
        wide = GetDWORDFromRegistry(name, "SizeX", 900)
        hi = GetDWORDFromRegistry(name, "SizeY", 900)
        x = GetDWORDFromRegistry(name, "PosX", 0)
        y = GetDWORDFromRegistry(name, "PosY", 0)
        max = GetDWORDFromRegistry(name, "Max", 0)
        if wx.NOT_FOUND == wx.Display(0).GetFromPoint((x, y)):  # check that the upper left is on screen, otherwise move the window
            x, y = wx.Display(0).Geometry.GetTopLeft()
        self.SetDimensions(x, y, wide, hi)
        if max:
            self.Maximize(True)  # calling self.Maximize(max) causes weird screen flicker if max=false

    def SavePerspective(self, rawpath=''):
        '''Save a file describing the gui window layout.
            Version number
            Frame Size tuple
            number of panes
            PANE DATA (one for each pane in manager):
                SavePaneInfo() data (where chart windows title bars are changed back to standard naming or LoadPane/LoadPersp may fail)
                window size for the pane
        '''
        import pickle
        f = open(rawpath, "wb")
        pickle.dump(2, f)  # version
        w, h = self.GetSize()
        pickle.dump([w, h], f)  # frame size
        x, y = self.GetPosition()
        pickle.dump([x, y], f)  # frame upper left coordinate -- added version 2
        pickle.dump(self.IsMaximized(), f)
        panes = self._mgr.GetAllPanes()
        pickle.dump([str(p.name) for p in panes], f)  # store the names for the layout so we can make sure they exist before LoadPerspective
        pickle.dump(self._mgr.SavePerspective(), f)  # the window layout for all docked and undocked panes.
        f.close()

    def LoadPerspective(self, rawpath=''):
        '''Override the CreateNeededPanes method if there are panes that are dynamically created and
            need to be made before the aui manager is updated.
        '''
        import pickle
        f = open(rawpath, "rb")
        ver = pickle.load(f)  # version
        w, h = pickle.load(f)
        self.SetSize((w, h))
        # storing upper left after version 1
        x, y = pickle.load(f)
        maxi = pickle.load(f)
        if wx.NOT_FOUND == wx.Display(0).GetFromPoint((x, y)) and wx.NOT_FOUND == wx.Display(0).GetFromPoint((x + 20, y + 20)):  # check that the upper left is on screen, otherwise move the window
            x, y = wx.Display(0).Geometry.GetTopLeft()
        self.SetPosition((x, y))
        if maxi:
            self.Maximize(True)

        loading_panes = set(pickle.load(f))
        perspective_string = pickle.load(f)
        current_panes = set([str(p.name) for p in self._mgr.GetAllPanes()])  # rebuild list after the plot notebooks are created
        self.CreateNeededPanes(loading_panes, current_panes)
        current_panes = set([str(p.name) for p in self._mgr.GetAllPanes()])  # rebuild list after the plot notebooks are created

        if current_panes.issuperset(loading_panes):  # we have successfully created all the windows we need -- otherwise loadperspective is buggy
            self._mgr.LoadPerspective(perspective_string)
        else:
            wx.MessageBox("Perspective (window layout) not loaded,\n there was an unsupported window name in the stored file.\nSee the console window and email HSTB.", "Failed to reload window layout", wx.OK | wx.CENTRE | wx.ICON_INFORMATION, None)
            print('*' * 50)
            print("Not all windows could be created, send the following list to HSTP if necessary")
            print('open windows:', current_panes)
            print('loading windows:', loading_panes)
            print('*' * 50)
        # We should now have panes with matching names to what was stored (to avoid exceptions in the LoadPerspective( ) )
        for p in [pane for pane in self._mgr.GetAllPanes() if pane.IsFloating()]:
            if wx.NOT_FOUND == wx.Display(0).GetFromPoint(p.floating_pos) and wx.NOT_FOUND == wx.Display(0).GetFromPoint(p.floating_pos + (20, 20)):
                p.FloatingPosition(wx.Display(0).Geometry.GetTopLeft())
                self._mgr.Update()
        f.close()

    def CreateNeededPanes(self, loading_panes, current_panes):
        '''Override the CreateNeededPanes method if there are panes that are dynamically created and
            need to be made before the aui manager is updated.
            loading_panes are the names of panes that were open on the last save call.
            current_panes are the windows currently open under the control of self._mgr (aui manager)
        '''

    def CreateShellWindow(self, addlocals, bShowFilling=False, bRefreshMgr=False, introtext=""):
        '''Simple wx.py shell.  Use as guid to create an aui managed window and/or for the python shell itself.
        '''
        self.shellbook = aui.AuiNotebook(self, -1,
                                         style=aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_TAB_MOVE | aui.AUI_NB_SCROLL_BUTTONS | aui.AUI_NB_WINDOWLIST_BUTTON | wx.WANTS_CHARS)
        self.shell = ShellWindow(self.shellbook, addlocals, introtext)
        self.shellbook.AddPage(self.shell, "shell")
        if bShowFilling:
            self.shell.AddFilling()
            self.shellbook.AddPage(self.shell.filling, "filling")
        self._mgr.AddPane(self.shellbook, aui.AuiPaneInfo().
                          Name("Shell").Caption("Shell").Layer(1).
                          Right().CloseButton(True).MaximizeButton(True))
        if bRefreshMgr:
            self._mgr.Update()

    def OnShowWidgetInspector(self, event=None):
        import wx.lib.inspection
        wx.lib.inspection.InspectionTool().Show()

    def OnShowHideShell(self, evt):
        p = self._mgr.GetPane('Shell')
        p.Show(not p.IsShown())
        self._mgr.Update()

    def CreateLog(self):
        '''Create a simple log/text window as the center window, the one that can't float
        '''
        # Set up a text control log window object and set the wx.Windows log target to it
        self.log = SelfClearingTextCtrl(self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self._mgr.AddPane(self.log, aui.AuiPaneInfo().Layer(0).
                          Name("Log").Caption("Log Window").CloseButton(False).MaximizeButton(False).Center())

    def CreateZToolBar(self):
        pass
    # def ZProcessEvent(self, event):
        #raise "must overide this function"
    # def CreateZFrameLayout(self):
        #raise "must overide this function"
        # example of making a dockable pane
        # self._mgr.AddPane(self.CreateTextCtrl(), aui.AuiPaneInfo().
        #                  Name("test10").Caption("Text Pane").
        #                  Bottom().Layer(1).Position(1).CloseButton(True).MaximizeButton(True))
        # def CreateTextCtrl(self):
        #   return wx.TextCtrl(self,-1, text, wx.Point(0, 0), wx.Size(150, 90), wx.NO_BORDER | wx.TE_MULTILINE)

    def CreateZTaskBar(self):
        icon = wx.Icon(PathToResource('Pydro.ico'), wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # setup a taskbar icon, and catch some events from it
        self.tbicon = TaskBarIcon()
        self.tbicon.SetIcon(icon, self.GetTitle())
        self.tbicon.Bind(EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.tbicon.Bind(EVT_TASKBAR_RIGHT_UP, self.OnTaskBarMenu)
        self.tbicon.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=self.TBMENU_RESTORE)
        self.tbicon.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)

    def CreateNewMenuBar(self, _InternalEvents, Menus, DisabledMenus):
        '''InternalEvents are a dict and have the form {"Name" : [object_or_module, FunctionToCall, ID] ... } (note the list since ID is filled)
        Menus are nested lists of list(Name, object_or_module, FunctionToCall, ID)
        FunctionToCall and ID are optional and assumed to be '' and -1 respectively if not supplied.
        If FunctionToCall is False (missing, '', None, False) then the function name is generated by the "Name"
          Leading AlphaNumerics with spaces and an optional leading "&" are grabbed,
          spaces are removed and "On" is prepended.  The result is used as FunctionToCall
          ex:
            'Show Tip' : 'OnShowTip'
            '&HSTP Help' : 'OnHSTPHelp'
            '&About\tCtrl-H' : 'OnAbout'
        ID is replaced by the wx.NewId() value if ID is -1
        then an event is registered
        wx.EVT_COMMAND(self, action[-1], wx.wxEVT_COMMAND_BUTTON_CLICKED, action[1])
        '''
        optionals = [-1, '']  # tack these on in reverse if no ID or Function name are supplied -- just making placeholders
        # create events for programatically created events
        for action in list(_InternalEvents.values()):
            if action.GetID() < 0:
                action.SetID(wx.NewId())
            self.Bind(wx.EVT_COMMAND, action.GetObj().__getattribute__(action.GetMethodName()), id=action.GetID(), id2=wx.wxEVT_COMMAND_BUTTON_CLICKED)

        # Make a main menu(s)
        self.mainmenu = wx.MenuBar()
        fullmenu = Menus + [self.help_menu]

        for heading in fullmenu:
            self.MakeMainSubMenu(heading, DisabledMenus)

        self.SetMenuBar(self.mainmenu)

        self.f2ID = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnF2, id=self.f2ID)
        helpID = [item.GetID() for item in self.help_menu.GetSubItems()[0] if item.GetText() == '&About\tCtrl-H'][0]
        aTable = wx.AcceleratorTable([(wx.ACCEL_ALT, ord('X'), self.exitID),
                                      (wx.ACCEL_CTRL, ord('H'), helpID),
                                      (wx.ACCEL_NORMAL, wx.WXK_F2, self.f2ID)])
        self.SetAcceleratorTable(aTable)

    def MakeMenuItem(self, add_to_menu, mitem, DisabledMenus=[]):
        if mitem.GetID() < 0:
            mitem.SetID(wx.NewId())
        add_to_menu.Append(mitem.GetID(), mitem.GetText())
        if mitem.GetText() in DisabledMenus:
            add_to_menu.Enable(mitem.GetID(), False)
        self.Unbind(wx.EVT_MENU, id=mitem.GetID())  # clear the event bindings if there are any
        try:
            self.Bind(wx.EVT_MENU, mitem.GetObj().__getattribute__(mitem.GetMethodName()), id=mitem.GetID())
        except:
            print('failed to create menu item,', mitem.GetMethodName())
            raise Exception('Failed to bind menu item ' + mitem.GetMethodName())

    def MakeSubMenu(self, menu, sections, DisabledMenus):
        for index, section in enumerate(sections):
            for i_g in section:  # group or item
                if isinstance(i_g, HSTPMenuGroup):
                    submenu = wx.Menu()
                    self.MakeSubMenu(submenu, i_g.GetSubItems(), DisabledMenus)
                    gMenu = menu.AppendSubMenu(submenu, i_g.GetText())
                    i_g.SetID(gMenu.GetId())
                    if i_g.GetText() in DisabledMenus:
                        gMenu.Enable(False)
                else:  # item
                    self.MakeMenuItem(menu, i_g, DisabledMenus)
            if (index < len(sections) - 1):  # separators excepts after the last section
                menu.AppendSeparator()

    def MakeMainSubMenu(self, heading, DisabledMenus):
        '''heading is a HSTPMenuGroup that will be add to the mainmenu
        Any menu with text of "&File" will have Recent Files and Exit items added
        '''
        menu = wx.Menu()
        self.MakeSubMenu(menu, heading.GetSubItems(), DisabledMenus)

        if heading.GetText() == '&File' and menu:
            menu.AppendSeparator()
            try:
                if self.exitID < 0:
                    self.exitID = wx.NewId()
            except AttributeError:
                self.exitID = wx.NewId()
            menu.Append(self.exitID, 'E&xit\tAlt-X')

            self.Bind(wx.EVT_MENU, self.OnFileExit, id=self.exitID)
            self.filehistory = wx.FileHistory()
            self.filehistory.UseMenu(menu)
            self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
            name = "\\" + self.appname + "\\RecentFiles"
            for k in range(9, -1, -1):
                p = GetPathFromRegistry("mru" + str(k), "", name)
                if p:
                    self.filehistory.AddFileToHistory(p)

        self.mainmenu.Append(menu, heading.GetText())

    def CreateZMenuBar(self, _InternalEvents, Menus, _Zevents, DisabledMenus):
        # create events for programatically created events
        for action in _InternalEvents:
            mID = _Zevents.get(action, wx.NewId())
            _Zevents[action] = mID
            # create a handler using the COMMAND_BUTTON, I'm afraid this may cause problems
            # by inadvertently using the same ID as a real button and conflicting
            self.Bind(wx.EVT_COMMAND, mID, wx.wxEVT_COMMAND_BUTTON_CLICKED, self.ZProcessEvent)

        # Make a main menu(s)
        self.mainmenu = wx.MenuBar()
        fullmenu = Menus
        for heading in fullmenu:
            menu = wx.Menu()
            menuhead, menulist = heading[:2]
            for group in menulist:
                for operation in group:
                    groupname, actions = operation[:2]
                    if (actions):
                        submenu = wx.Menu()
                        for action in actions:
                            if action:
                                mID = _Zevents.get(action, wx.NewId())
                                submenu.Append(mID, action)
                                if action in DisabledMenus:
                                    submenu.Enable(mID, False)
                                _Zevents[action] = mID
                                self.Bind(wx.EVT_MENU, self.ZProcessEvent, id=mID)
                            else:
                                submenu.AppendSeparator()
                        mID = _Zevents.get(groupname, wx.NewId())
                        menu.AppendMenu(mID, groupname, submenu)
                        _Zevents[groupname] = mID
                    else:
                        mID = _Zevents.get(groupname, wx.NewId())
                        menu.Append(mID, groupname)
                        if groupname in DisabledMenus:
                            menu.Enable(mID, False)
                        _Zevents[groupname] = mID
                        self.Bind(wx.EVT_MENU, self.ZProcessEvent, id=mID)
                if (group != menulist[-1]):
                    menu.AppendSeparator()

            if menuhead == '&File':
                menu.AppendSeparator()
                emailhelp = wx.NewId()
                menu.Append(emailhelp, 'Email Support')
                trachelpID = wx.NewId()
                menu.Append(trachelpID, 'Online Support')
                exitID = wx.NewId()
                menu.Append(exitID, 'E&xit\tAlt-X')

                self.Bind(wx.EVT_MENU, self.EmailHelpRequest, id=emailhelp)
                self.Bind(wx.EVT_MENU, self.OnFileExit, id=exitID)
                self.filehistory = wx.FileHistory()
                self.filehistory.UseMenu(menu)
                self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
                name = "\\" + self.appname + "\\RecentFiles"
                for k in range(9, -1, -1):
                    p = GetPathFromRegistry("mru" + str(k), "", name)
                    if p:
                        self.filehistory.AddFileToHistory(p)

            self.mainmenu.Append(menu, menuhead)

        # Make a Help menu
        menu = wx.Menu()
        showtipID = wx.NewId()
        menu.Append(showtipID, 'Show Tip')
        hstphelpID = wx.NewId()
        menu.Append(hstphelpID, '&HSTP Help')
        pydrowebsiteID = wx.NewId()
        menu.Append(pydrowebsiteID, 'Online Pydro Docs')
        menu.Append(trachelpID, 'Online Support')
#        changelogid = wx.NewId()
        # menu.Append(changelogid, 'Change Log')
#        futurechangelogid = wx.NewId()
#        menu.Append(futurechangelogid, 'Upcoming Changes')
        if Constants.UseDebug():  # Control debug stuff (=0 to hide debug menu et al from users in the field)
            PeekhelpID = wx.NewId()
            menu.Append(PeekhelpID, '&PeekXTF Help')
            self.Bind(wx.EVT_MENU, self.ShowPeekHelp, id=PeekhelpID)
            MTPhelpID = wx.NewId()
            menu.Append(MTPhelpID, '&MidTierPeek Help')
            self.Bind(wx.EVT_MENU, self.ShowMTPHelp, id=MTPhelpID)
        helpID = wx.NewId()
        menu.Append(helpID, '&About\tCtrl-H')
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=helpID)
        self.Bind(wx.EVT_MENU, self.OnDocsWebsite, id=pydrowebsiteID)
        self.Bind(wx.EVT_MENU, self.OnTracWebsite, id=trachelpID)
        self.Bind(wx.EVT_MENU, self.ShowTip, id=showtipID)
        self.Bind(wx.EVT_MENU, self.ShowHelp, id=hstphelpID)
#        self.Bind(wx.EVT_MENU, self.OnChangeLog, id=changelogid)
#        self.Bind(wx.EVT_MENU, self.OnFutureChangeLog, id=futurechangelogid)

        self.mainmenu.Append(menu, '&Help')

        self.SetMenuBar(self.mainmenu)

        f2ID = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnF2, id=f2ID)
        aTable = wx.AcceleratorTable([(wx.ACCEL_ALT, ord('X'), exitID),
                                      (wx.ACCEL_CTRL, ord('H'), helpID),
                                      (wx.ACCEL_NORMAL, wx.WXK_F2, f2ID)])
        self.SetAcceleratorTable(aTable)
#    def OnChangeLog(self, event):
#        '''Override this method to get a different changelog-- defaults to all pydro changes'''
#        try:
#            txt= upgrade.GetExistingChanges('', PathToApp+"..")
#            txt=['Below should be the list of changes made in this release of Pydro.\n']+txt
#            self.ShowChangeLog(txt)
#        except:
#            if _dHSTP:
#                import traceback
#                traceback.print_exc()
#            print( "Failed to download changelog")
#    def OnFutureChangeLog(self, event):
#        '''Check the Trunk for modifictations that come after the installed version'''
#        try:
#            txt= upgrade.GetPatchChanges(upgrade.PydroSVNUrl, PathToApp+"..")
#            txt=['Any changes made at HSTP that are available in a patch more recent than is being run',
#                    'or that are not available publicly yet should be shown below.',
#                    'This is to help you know what features are added and bugs are fixed in an upcoming release\n'] + txt
#            self.ShowChangeLog(txt)
#        except:
#            if _dHSTP:
#                import traceback
#                traceback.print_exc()
#            print( "Failed to download changelog")
#    def ShowChangeLog(self, txt):
#        try:
#            f=open(PathToApp+'pydrochangelog.txt', 'wb')
#            f.write('\r\n'.join(txt))
#            f.close()
#            import win32api, win32con
#            win32api.ShellExecute(0, 'open', PathToApp+'pydrochangelog.txt', None, "", win32con.SW_SHOW)
#        except:
#            print( 'Failed to save/display change log --\n ..\\pydrochangelog.txt was in use or the associated text viewer failed.')

    def OnF2(self, event):
        pass

    def CreateZStatusBar(self):
        self.sbar = self.CreateStatusBar(1, STB_SIZEGRIP)  # Create a status bar--start with 1 field, then specify actual #...
        nfields = 2
        self.sbar.SetFieldsCount(nfields)   # start with 2 w/default widths [-1,-1]; apps add more

    def OnSize(self, event):
        self.ResizeStatusBar()
        event.Skip()

    def ResizeStatusBar(self):
        pass  # used to position progress bars

    def OnIdle(self, event):
        pass

    def OnFileHistory(self, event):
        pass

    def OnFileExit(self, event):
        # need to spawn an event that MainFrame is dying so derived objects can clean up (i.e., Pydro SavePSS?)
        self.Close()

    #---------------------------------------------
    def OnHelpAbout(self, event):
        about = About.MyAboutBox(self)
        about.ShowModal()
        about.Destroy()

    def OnDocsWebsite(self, event):
        win32api.ShellExecute(0, None, "http://trac.pydro.noaa.gov/", None, '', win32con.SW_SHOW)   # should launch default browser

    def OnTracWebsite(self, event):
        win32api.ShellExecute(0, None, "http://trac.pydro.noaa.gov/report", None, '', win32con.SW_SHOW)   # should launch default browser

    #---------------------------------------------
    def OnCloseWindow(self, event):
        try:
            self.SavePerspective(self.default_persp)
        except:
            self.SavePos()

        # win32help.HtmlHelp(0, None, win32help.HH_UNINITIALIZE, self.help_handle)

        self._mgr.UnInit()
        name = "\\" + self.appname + "\\RecentFiles"
        try:
            cnt = self.filehistory.GetNoHistoryFiles()
        except AttributeError:
            cnt = self.filehistory.GetCount()
        for n in range(cnt):
            p = self.filehistory.GetHistoryFile(n)
            SavePathToRegistry("mru" + str(n), p, name)
        self.window = None
        self.mainmenu = None
        if hasattr(self, "tbicon"):
            self.tbicon.Destroy()  # not destroying the tbicon makes the program hang.
            del self.tbicon
        self.Destroy()

    def OnTaskBarActivate(self, evt):
        if self.IsIconized():
            self.Iconize(False)
        if not self.IsShown():
            self.Show(True)
        self.Raise()

    TBMENU_RESTORE = 1000
    TBMENU_CLOSE = 1001

    def OnTaskBarMenu(self, evt):
        menu = wx.Menu()
        menu.Append(self.TBMENU_RESTORE, "Show " + self.GetTitle())
        self.tbicon.PopupMenu(menu)
        menu.Destroy()

    def OnTaskBarClose(self, evt):
        self.Close()

        # because of the way wx.TaskBarIcon.PopupMenu is implemented we have to
        # prod the main idle handler a bit to get the window to actually close
        wx.GetApp().ProcessIdle()

    def ShowHelp(self, event=None, topic=None):
        # win32api.ShellExecute(0,"open", PathToApp+"HSTPHelp.chm", None,"",1)
        s = PathToApp + "HSTPHelp.chm"
        if topic:
            s += "::" + topic  # "/PydroFiles/FeatureTree.html" for example
        hw = win32help.HtmlHelp(0, s, win32help.HH_DISPLAY_TOPIC, None)

    def ShowPeekHelp(self, event=None):
        win32api.ShellExecute(0, "open", PathToApp + "PeekXTF.chm", None, "", 1)

    def ShowMTPHelp(self, event=None):
        win32api.ShellExecute(0, "open", PathToApp + "MidTierPeek.chm", None, "", 1)

    def ShowTip(self, event=None):
        if self.TipFilename:
            try:
                showTipText = open(PathToApp + self.TipFilename).read()
                showTip, index = eval(showTipText)
            except IOError:
                showTip, index = (1, 0)
            if showTip or event:
                tp = wx.CreateFileTipProvider(PathToApp + self.TipFilename + ".txt", index)
                showTip = wx.ShowTip(self, tp)
                index = tp.GetCurrentTip()
                open(PathToApp + self.TipFilename, "w").write(str((showTip, index)))


import wx.lib.agw.aui as agw_aui


class HSTP_AGW_Frame(HSTP_AUI_Frame):

    def __init__(self, parent, id, title, RegistryAppName, InternalEvents, Menus, _Zevents, DisabledMenus=[], newMenus=[]):
        '''Menus should be laid out as following: @TODO -- change to ordered dictionary in a future version of python
        [[MenuName,[MenuItem, MenuItem]], [SecondMenuName, [MenuItem, MenuItem]]]
        A MenuItem can either be [ItemName, object, attribute, menu_id]
            object would be the class instance or a modulename,
            attribute is the function to call from the event handler
            menu_id should be specified as -1 and will be filled by the generated menu_id
            This eventually creates the following call
            wx.EVT_MENU(self, menu_id, object.__getattribute__(attribute))
            [['File,['Open', self, 'OnFileOpen', -1]], ['Window',['Preferences', self, 'OnPref',-1]]] would be an example

        '''
        wx.Frame.__init__(self, parent, -1, title, size=(800, 600),
                          style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        # tell FrameManager to manage this frame
        self._mgr = agw_aui.AuiManager()
        try:
            self._mgr.SetFlags(agw_aui.AUI_MGR_DEFAULT | agw_aui.AUI_MGR_ALLOW_ACTIVE_PANE)
        except AttributeError:
            pass
        self._mgr.SetManagedWindow(self)

        # self.help_handle = win32help.HtmlHelp(0, None, win32help.HH_INITIALIZE)[1]

        self.appname = RegistryAppName
        self.SetTips(None)  # apps should set as appropriate after instantiating a MainFrame object

        # default windows behaviour is for child frames to always be on top of parent - to overcome this use None as parent and
        # list frames here that are parented to desktop so that they can be overlapped by parent
        self.CreateZTaskBar()
        if newMenus:
            G = HSTPMenuGroup
            I = HSTPMenuItem
            self.help_menu = G('&Help', [
                [
                    I('Show Tip', self, 'ShowTip', -1),
                    I('&HSTP Help', self, 'ShowHelp', -1),
                    I('Online Pydro Docs', self, 'OnDocsWebsite', -1),
                    I('Online Support', self, 'OnDocsWebsite', -1),
                    I('Email Support', self, 'EmailHelpRequest'),
                    I('Turn On AutoUpdate at Startup', self, 'AutoUpdateOn'),
                    I('Turn Off AutoUpdate at Startup', self, 'AutoUpdateOff'),
                    #I('Change Log', self, '', -1),
                    #I('Upcoming Changes', self, 'OnFutureChangeLog', -1),
                    I('&About\tCtrl-H', self, 'OnHelpAbout', -1),
                ]
            ]
            )
            if Constants.UseDebug():  # Control debug stuff (=0 to hide debug menu et al from users in the field)
                self.help_menu.AppendItem(I('&PeekXTF Help', self, 'ShowPeekHelp', -1))
                self.help_menu.AppendItem(I('&MidTierPeek Help', self, 'ShowMTPHelp', -1))
                self.help_menu.AppendItem(I('&Show/Hide Shell', self))
                self.help_menu.AppendItem(I('&Show Widget Inspector', self))

            self.CreateNewMenuBar(InternalEvents, newMenus, DisabledMenus)
        else:
            self.CreateZMenuBar(InternalEvents, Menus, _Zevents, DisabledMenus)
        self.CreateZToolBar()
        self.CreateZStatusBar()

        self.CreateZFrameLayout()
        self.default_persp = PathToApp + self.appname + '.default.psl'
        try:
            self.LoadPerspective(self.default_persp)
        except:
            self.RestorePos()

        # Some generic handler declarations for ZoomelatorFrame
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        # Show How To Use The Closing Panes Event
        self.Bind(agw_aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)

    def CreateShellWindow(self, addlocals, bShowFilling=False, bRefreshMgr=False, introtext=""):
        '''Simple wx.py shell.  Use as guid to create an aui managed window and/or for the python shell itself.
        '''
        self.shellbook = agw_aui.AuiNotebook(self, -1,
                                             style=agw_aui.AUI_NB_TAB_SPLIT | agw_aui.AUI_NB_TAB_MOVE | agw_aui.AUI_NB_SCROLL_BUTTONS | agw_aui.AUI_NB_WINDOWLIST_BUTTON | wx.WANTS_CHARS)
        self.shell = ShellWindow(self.shellbook, addlocals, introtext)
        self.shellbook.AddPage(self.shell, "shell")
        if bShowFilling:
            self.shell.AddFilling()
            self.shellbook.AddPage(self.shell.filling, "filling")
        self._mgr.AddPane(self.shellbook, agw_aui.AuiPaneInfo().
                          Name("Shell").Caption("Shell").Layer(1).
                          Right().CloseButton(True).MaximizeButton(True))
        if bRefreshMgr:
            self._mgr.Update()

    def CreateLog(self):
        '''Create a simple log/text window as the center window, the one that can't float
        '''
        # Set up a text control log window object and set the wx.Windows log target to it
        self.log = SelfClearingTextCtrl(self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self._mgr.AddPane(self.log, agw_aui.AuiPaneInfo().Layer(0).Floatable(False).
                          Name("Log").Caption("Log Window").CloseButton(False).MaximizeButton(False).Center())


_PydroVersion = Constants.PydroTitleVersion()


class SplashScreenApp(wx.App):

    def OnInit(self):
        """
        Create and show the splash screen.  It will then create and show
        the main frame when it is time to do so.
        """
        from PIL import Image, ImageFont, ImageDraw

        # For debugging
        # self.SetAssertMode(wx.PYAPP_ASSERT_DIALOG)
        if _dHSTP:
            try:
                self.SetAssertMode(wx.PYAPP_ASSERT_DIALOG)  # added in wxPython 2.3.4.2
            except AttributeError:
                self.SetAssertMode(wx.APP_ASSERT_DIALOG)  # added in wxPython 2.3.4.2
        else:
            try:
                self.SetAssertMode(wx.PYAPP_ASSERT_SUPPRESS)  # don't show wxPython warnings
            except AttributeError:
                self.SetAssertMode(wx.APP_ASSERT_SUPPRESS)  # don't show wxPython warnings

        f = Image.open(PathToResource('PydroSplashBase.jpg'))
        try:
            imfont = ImageFont.truetype("arial.ttf", 36)
            d = ImageDraw.Draw(f)
            d.text((5, f.size[1] - imfont.getsize('Pydro v' + str(_PydroVersion))[1] - 5), 'Pydro v' + str(_PydroVersion), font=imfont)
        except:
            pass
        f.save(PathToResource('PydroSplash.jpg'))
        bmp = wx.Image(PathToResource("PydroSplash.jpg")).ConvertToBitmap()
        SplashScreen(bmp, SPLASH_CENTRE_ON_SCREEN | SPLASH_TIMEOUT,
                     1500, None, -1)
        return self.ShowMain()

# Must Override the ShowMain with the window/frame to create
#    def ShowMain(self):
#        frame = PydroFrame(None, -1, "Pydro v%s"%_PydroVersion) # wxDefaultPosition, wxSize?
#        frame.Show(True)
#        #self.SetTopWindow(frame)
#        frame.ShowTip()
#
#        return True


class SampleFrame(HSTP_AUI_Frame):

    def __init__(self, parent, id, title):
        G = HSTPMenuGroup
        I = HSTPMenuItem
        self._ZfileMenu = G('&File')  # needed to allow File exit and online support menu items
        self._TestMenu = G('&Misc', [[
            G('CO-OPS', [[I('Test Sub', self, 'SubFunc', -1)]], -1),
            I('Test 1', self),  # Show the no function or ID optional fields -- filled when CreateNewMenu is executed
        ], [
            I('Reload', self, 'Reload'),  # Supply a Name but no ID
        ]]
        )
        self._InternalEvents = {'TestInternal': I('', self, 'Test2', -1)}
        _Zevents = {}  # dictionary to keep events in
        fullmenu = [self._ZfileMenu, self._TestMenu]
        DisableMenus = ['Test 2', ]
        HSTP_AUI_Frame.__init__(self, parent, -1, title, "SampleFrame", self._InternalEvents, [], _Zevents, DisableMenus, fullmenu)

    def OnTest1(self, event):
        self.log.write('Test 1 menu item, trying internal message\n')
        ev = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self._InternalEvents['TestInternal'].GetID())
        self.ProcessEvent(ev)

    def Test2(self, event):
        self.log.write('Received Internal Message\n')

    def SubFunc(self, event):
        self.log.write('SubFunc post1 menu clicked')

    def CreateZFrameLayout(self):
        self.CreateLog()  # Create self.log
        wx.Log_SetActiveTarget(wx.LogTextCtrl(self.log))
        self.CreateTree()
        self.CreateShellWindow({'frame': self})
        self._mgr.Update()  # "commit" all changes made to FrameManager

    def CreateTree(self):
        # Set up the contact tree control with log window
        import wx.lib.customtreectrl as CT
        try:
            self.tree = CT.CustomTreeCtrl(self, -1, wx.DefaultPosition, wx.DefaultSize, agwStyle=wx.SUNKEN_BORDER | CT.TR_HAS_BUTTONS | CT.TR_HAS_VARIABLE_ROW_HEIGHT | wx.WANTS_CHARS)
        except:
            self.tree = CT.CustomTreeCtrl(self, -1, wx.DefaultPosition, wx.DefaultSize, style=wx.SUNKEN_BORDER | CT.TR_HAS_BUTTONS | CT.TR_HAS_VARIABLE_ROW_HEIGHT | wx.WANTS_CHARS)

        root = self.tree.AddRoot("The Root Item")

        for n in range(15):
            child = self.tree.AppendItem(root, "Item %d" % n)
        self._mgr.AddPane(self.tree, aui.AuiPaneInfo().
                          Name("Tree").Caption("Feature Tree").
                          Left().Layer(1).CloseButton(True).MaximizeButton(True).FloatingSize((400, 400)))

    def Reload(self, event):
        import BaseAuiFrame  # reload this module
        importlib.reload(BaseAuiFrame)
        self.__class__ = BaseAuiFrame.SampleFrame  # repoint the __class__ attribute to the new bytecode
        self._TestMenu.AppendItem(HSTPMenuItem('dynamic add menu item', BaseAuiFrame, 'DoNothing'))
        self.CreateNewMenuBar(self._InternalEvents, [self._ZfileMenu, self._TestMenu], [])
        # self.UpdateMenus(self._InternalEvents, [self._ZfileMenu, self._TestMenu])
        self.log.write('Reloaded BaseAUIFrame\n')


def DoNothing(event):
    print('Hi, doing nothing', event.GetId())


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    class DemoApp(SplashScreenApp):

        def ShowMain(self):
            frame = SampleFrame(None, -1, "Pydro v%s" % _PydroVersion)  # wxDefaultPosition, wxSize?
            frame.Show(True)
            # self.SetTopWindow(frame)
            # frame.ShowTip()

            return True

    app = DemoApp(0)
    app.MainLoop()
    # import hotshot
    # profiler = hotshot.Profile("test.profile")
    # command = '''app.MainLoop()'''
    # profiler.runctx(command,globals(),locals())
    # profiler.close()
