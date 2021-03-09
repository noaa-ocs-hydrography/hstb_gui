#!/usr/bin/env python

import multiprocessing
import win32api
import win32con

import wx

from .PyCGProgress import PyProgress
from HSTB.shared import RegistryHelpers

# you have to use "with" statements when using the progress classes.
# An exception will hang the program with the other progress processes still alive
# see demo code at bottom.


class ProgApp(wx.App):
    name = "Progbar\\position"

    def OnInit(self):
        return True

    def Setup(self, conn, bars, title='Progress', style=wx.PD_ELAPSED_TIME | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE):
        ''' bars is a list of lists describing the progress bars to display.
        One progress bar will be created for each item in the bars object.
        Each item contains (min, max, text), for example:
        [[0,9,"test"], [0,20,"test2"]]
        Generates two progress bars with the top on ranging from 0 to 9 and the bottom ranging from 0 to 20 with the
        respective text inside the progress bars.
        '''
        self.dlg_position = self.RetrievePos()
        self.dlg = PyProgress(bars,
                              title=title,
                              style=style,
                              loc=self.dlg_position)
        # style = wx.PD_AUTO_HIDE
        # |wx.PD_CAN_ABORT
        # | wx.PD_APP_MODAL
        # | wx.PD_ELAPSED_TIME
        # |wx.PD_SMOOTH
        # | wx.PD_ESTIMATED_TIME
        # | wx.PD_REMAINING_TIME
        ID_Timer = wx.NewId()
        self.conn = conn
        self.AutoTimer = wx.Timer(self, ID_Timer)
        self.Bind(wx.EVT_TIMER, self.OnTimer, id=ID_Timer)
        self.AutoTimer.Start(50)
        return True

    def OnTimer(self, event):
        try:
            # print 'tick'
            if self.conn.poll():
                data = []
                keepGoing = True
                while self.conn.poll():
                    bars = self.conn.recv()
                    # since we may be skipping the display of message we need to track any caption/label changes and make sure they take effect
                    for b, bar in enumerate(bars):
                        if len(data) <= b:
                            data.append([])
                        try:
                            for i, v in enumerate(bar):
                                if v or i == 0:  # replace caption/label if non-empty string (always replace value)
                                    data[b][i] = v
                        except:
                            data[b] = bar
                keepGoing = self.dlg.Update(*data)
                self.dlg_position = self.dlg.GetPosition()
                if not keepGoing:
                    raise IOError('user stopped')
        except (IOError, EOFError):
            # connection closed -- close the window
            self.AutoTimer.Stop()
            self.dlg.Close()
            self.dlg.Destroy()
            # self.Close()
        # print 'leaving timer'

    def OnExit(self):
        self.SavePos()
        return 0

    def SavePos(self):
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
        pos = self.dlg_position
        if (pos[0] >= minx and pos[0] <= maxx) and (pos[1] >= miny and pos[1] <= maxy):   # Don't save if Pydro is minimized to Task Bar, or window is off screen
            RegistryHelpers.SaveDWORDToRegistry(self.name, "PosX", pos[0])
            RegistryHelpers.SaveDWORDToRegistry(self.name, "PosY", pos[1])

    def RetrievePos(self):
        x = RegistryHelpers.GetDWORDFromRegistry(self.name, "PosX", 0)
        y = RegistryHelpers.GetDWORDFromRegistry(self.name, "PosY", 0)
        if win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) != 0:
            minx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN) - 20
            miny = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN) - 20
            maxx = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) + minx
            maxy = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN) + miny
        else:  # not NT 5.0+ or win98+
            minx, miny = -20, -20
            maxx = win32api.GetSystemMetrics(win32con.SM_CXSCREEN) + minx
            maxy = win32api.GetSystemMetrics(win32con.SM_CYSCREEN) + miny
        if (x >= minx and x <= maxx) and (y >= miny and y <= maxy):   # Don't save if Pydro is minimized to Task Bar, or window is off screen
            return x, y
        else:
            return (0, 0)


def ProgDialog(conn, bars, title='Progress', style=wx.PD_ELAPSED_TIME | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE):
    app = ProgApp(0)
    app.Setup(conn, bars, title, style)
    app.MainLoop()


class MultiProgress:
    def __init__(self, bars=[[0, 100, 'Progress']], title='Progress', style=wx.PD_ELAPSED_TIME | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE, minimize=None):
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=ProgDialog, args=(self.child_conn, bars, title, style))
        p.start()
        try:
            self.win = minimize
            while self.win.GetParent():
                self.win = self.win.GetParent()
            self.win.Iconize(True)
        except:
            pass

    def Update(self, barValues):
        '''barValues is a list of lists where the progress bars are updated in order.
        An empty list specifies not to update.  An empty or missing caption or label yields no change.
        [[5, 'text 5','', 10], [7,'','Test %%.0f']]
        # updates first bar with value=5, caption="text 5" and does not modify the progress bars internal label, resets the maximum to 10.
        #   updates the second bar with value =7, no change to caption, and changes the internal label to Test %.0f to show the progress percentage

        [[], [n,'']] # does not modify the first progress bar and only changes the position/value of the second.
        '''
        self.parent_conn.send(barValues)

    def Close(self):
        try:
            self.win.Iconize(False)
        except:
            pass
        self.parent_conn.close()
        # p.join()

    def __del__(self):
        self.Close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.Close()


class SingleProgress(MultiProgress):
    def __init__(self, vmin=0, vmax=100, vtxt='Progress', **vargs):
        self.lastPosition = vmin
        MultiProgress.__init__(self, [[vmin, vmax, vtxt]], **vargs)

    def Update(self, cur=0, barcaption='', bartxt="", newmax=None, newmin=None):
        self.lastPosition = cur
        self.parent_conn.send([[cur, barcaption, bartxt, newmax, newmin]])

    def DllUpdate(self, cur, tot, txt=''):  # update the top bar via DLL callback
        '''This is the calling syntax used from PeekXTF and MidTierPeek DLLs to the Python functions that update progress bars'''
        self.Update(cur, '', txt, tot)

    def Increment(self, i=1):
        try:
            self.lastPosition += i
            self.parent_conn.send([[self.lastPosition]])
        except:
            pass


class ExcessingProgress(MultiProgress):
    '''Specialized for the progress callbacks in the PeekXTF DLL.  Don't know the max (it's supplied from the DLL callback).
    This has two bars in the progress window.'''

    def __init__(self, vtxt1='Progress', vtxt2='Progress', **vargs):
        MultiProgress.__init__(self, [[0, 100, vtxt1], [0, 100, vtxt2]], **vargs)

    def Update1(self, cur=0, tot=None, txt=''):  # update the top bar via DLL callback
        self.Update([[cur, '', txt, tot]])

    def Update2(self, cur=0, tot=None, txt=''):  # update the bottom bar from DLL callback
        # self.parent_conn.send([[],[cur, '',  '', tot]])
        self.Update([[], [cur, '', txt, tot]])


class PDFDocProgress(SingleProgress):
    def __init__(self, *args, **vargs):
        SingleProgress.__init__(self, *args, **vargs)

    def Update(self, typ, value):
        if typ == "SIZE_EST":
            self.estProgresses = value
            SingleProgress.Update(self, 0, '', "%.1f%% document built", value)
        elif typ == "PROGRESS":
            SingleProgress.Update(self, value)
        elif typ == "FINISHED":
            SingleProgress.Update(self, self.estProgresses)


class GDALProgress(MultiProgress):
    '''Specialized for the callbacks from the GDAL DLLs, value range is 0 to 1.0 '''

    def __init__(self, **args):
        MultiProgress.__init__(self, [[0, 1000.0, 'Loading Raster']], **args)

    def Update(self, cur=None, msg=None, txt=""):
        self.parent_conn.send([[cur * 1000.0, '', txt]])
        if msg:
            print(msg)
