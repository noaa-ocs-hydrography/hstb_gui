# --------------------------------------------------------------------------------- #
# PYPROGRESS wxPython IMPLEMENTATION
#
# Andrea Gavana, @ 03 Nov 2006
# Latest Revision: 03 Nov 2006, 22.30 CET
#
#
# TODO List
#
# 1. Do we support all the styles of wx.ProgressDialog in indeterminated mode?
#
# 2. Other ideas?
#
#
# For All Kind Of Problems, Requests Of Enhancements And Bug Reports, Please
# Write To Me At:
#
# gavana@kpo.kz
# andrea.gavana@gmail.com
#
# Or, Obviously, To The wxPython Mailing List!!!
#
#
# End Of Comments
# --------------------------------------------------------------------------------- #

"""
Description
===========

PyProgress is similar to wx.ProgressDialog in indeterminated mode, but with a
different gauge appearance and a different spinning behavior. The moving gauge
can be drawn with a single solid colour or with a shading gradient foreground.
The gauge background colour is user customizable.
The bar does not move always from the beginning to the end as in wx.ProgressDialog
in indeterminated mode, but spins cyclically forward and backward.
Other options include:

  - Possibility to change the proportion between the spinning bar and the
    entire gauge, so that the bar can be longer or shorter (the default is 20%);
  - Modifying the number of steps the spinning bar performs before a forward
    (or backward) loop reverses.

PyProgress can optionally display a Cancel button, and a wx.StaticText which
outputs the elapsed time from the starting of the process.


Supported Platforms
===================

PyProgress has been tested on the following platforms:
  * Windows (Windows XP);
  * Linux Ubuntu (Dapper 6.06)


License And Version:
===================

PyProgress is freeware and distributed under the wxPython license.


Latest Revision: Andrea Gavana @ 03 Nov 2006, 22.30 CET
Version 0.1

"""

__docformat__ = "epytext"


import wx

# Some constants, taken straight from wx.ProgressDialog
Uncancelable = -1
Canceled = 0
Continue = 1
Finished = 2

# Margins between gauge and text/button
LAYOUT_MARGIN = 8


# ---------------------------------------------------------------------------- #
# Class ProgressGauge
# ---------------------------------------------------------------------------- #

from . import ColorProgress
import time

# Class PyProgress
# ---------------------------------------------------------------------------- #


class PyProgress(wx.Dialog):
    """
    """

    def __init__(self, barMinMaxTxt=[[0, 100, ''], ], parent=None, id=-1, title="", message="",
                 style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE, loc=None):
        """ Default class constructor. """

        wx.Dialog.__init__(self, parent, id, title, style=wx.RESIZE_BORDER | wx.CAPTION | wx.MINIMIZE_BOX | wx.SYSTEM_MENU)

        self._delay = 3
        self._hasAbortButton = False

        # we may disappear at any moment, let the others know about it
        self.SetExtraStyle(self.GetExtraStyle() | wx.WS_EX_TRANSIENT)

        self._hasAbortButton = (style & wx.PD_CAN_ABORT)

        if wx.Platform == "__WXMSW__":
            # we have to remove the "Close" button from the title bar then as it is
            # confusing to have it - it doesn't work anyhow
            # FIXME: should probably have a (extended?) window style for this
            if not self._hasAbortButton:
                self.EnableClose(False)

        self._state = (self._hasAbortButton and [Continue] or [Uncancelable])[0]
        self._parentTop = wx.GetTopLevelParent(parent)

        dc = wx.ClientDC(self)
        dc.SetFont(wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT))
        widthText, dummy = dc.GetTextExtent(message)
        for bar in barMinMaxTxt:  # get rough widths of the progress bars
            try:
                widthText = max(widthText, 2 * dc.GetTextExtent(bar[2])[0])
            except:
                pass
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.Msgs = []
        self.CGProgress = []
        sizeDlg = wx.Size()
        for pmin, pmax, txt in barMinMaxTxt:
            self.Msgs.append(wx.StaticText(self, wx.ID_ANY, message))
            sizer.Add(self.Msgs[-1], 0, wx.LEFT | wx.TOP, 2 * LAYOUT_MARGIN)

            sizeLabel = self.Msgs[-1].GetSize()
            sizeDlg.y += 2 * LAYOUT_MARGIN + sizeLabel.y

            self.CGProgress.append(ColorProgress.ColorProgress(self, -1, style=0))  # CGProgClass(self.sbar, -1, style=0)
            prog = self.CGProgress[-1]
            self.SetupProgressBar(prog, pmin, pmax, txt)
            prog.ShowDosPrint()
            prog.ShowPercent()
            # prog.SetText("%.1f%%")
            # prog.position=0
            # self.statusbox.Add(self.CGProgress, 1, wx.EXPAND)
            sizer.Add(prog, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 2 * LAYOUT_MARGIN)

            sizeGauge = prog.GetSize()
            sizeDlg.y += 2 * LAYOUT_MARGIN + sizeGauge.y

        # create the estimated/remaining/total time zones if requested
        self._elapsed = None
        self._display_estimated = self._last_timeupdate = self._break = 0
        self._ctdelay = 0

        label = None

        nTimeLabels = 0

        if style & wx.PD_ELAPSED_TIME:

            nTimeLabels += 1
            self._elapsed = self.CreateLabel("Elapsed time : ", sizer)
            ID_Timer = wx.NewId()
            self.AutoTimer = wx.Timer(self, ID_Timer)
            self.Bind(wx.EVT_TIMER, self.OnTimer, id=ID_Timer)
            self.AutoTimer.Start(100)

        if nTimeLabels > 0:

            label = wx.StaticText(self, -1, "")
            # set it to the current time
            self._timeStart = time.time()
            sizeDlg.y += nTimeLabels * (label.GetSize().y + LAYOUT_MARGIN)
            label.Destroy()

        sizeDlgModified = False

        if wx.Platform == "__WXMSW__":
            sizerFlags = wx.ALIGN_RIGHT | wx.ALL
        else:
            sizerFlags = wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM | wx.TOP

        if self._hasAbortButton:
            buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

            self._btnAbort = wx.Button(self, -1, "Cancel")
            self._btnAbort.Bind(wx.EVT_BUTTON, self.OnCancel)

            # Windows dialogs usually have buttons in the lower right corner
            buttonSizer.Add(self._btnAbort, 0, sizerFlags, LAYOUT_MARGIN)

            if not sizeDlgModified:
                sizeDlg.y += 2 * LAYOUT_MARGIN + wx.Button.GetDefaultSize().y

        if self._hasAbortButton:
            sizer.Add(buttonSizer, 0, sizerFlags, LAYOUT_MARGIN)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self._windowStyle = style

        self.SetSizerAndFit(sizer)

        sizeDlg.y += 2 * LAYOUT_MARGIN

        # try to make the dialog not square but rectangular of reasonable width
        sizeDlg.x = max(widthText + 100, 4 * sizeDlg.y / 3)
        sizeDlg.x *= 3
        sizeDlg.x /= 2
        self.SetClientSize(sizeDlg)

        self.Centre(wx.BOTH)

        if loc:
            self.SetPosition(loc)

        if style & wx.PD_APP_MODAL:
            self._winDisabler = wx.WindowDisabler(self)
        else:
            if self._parentTop:
                self._parentTop.Disable()
            self._winDisabler = None

        self.ShowDialog()
        self.Enable()

        # this one can be initialized even if the others are unknown for now
        # NB: do it after calling Layout() to keep the labels correctly aligned
        if self._elapsed:
            self.SetTimeLabel(0, self._elapsed)

        self.evtloop = None

        # This is causing the unittests to hang, investigate it later.
        # if not wx.EventLoopBase.GetActive():
        #    self.evtloop = wx.GetApp().GetTraits().CreateEventLoop()
        #    wx.EventLoopBase.SetActive(self.evtloop)

        self.Update()

    def CreateLabel(self, text, sizer):
        """ Creates the wx.StaticText that holds the elapsed time label. """

        locsizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy = wx.StaticText(self, wx.ID_ANY, text)
        label = wx.StaticText(self, wx.ID_ANY, "unknown")

        if wx.Platform in ["__WXMSW__", "__WXMAC__"]:
            # label and time centered in one row
            locsizer.Add(dummy, 1, wx.ALIGN_LEFT)
            locsizer.Add(label, 1, wx.ALIGN_LEFT | wx.LEFT, LAYOUT_MARGIN)
            sizer.Add(locsizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, LAYOUT_MARGIN)
        else:
            # label and time to the right in one row
            sizer.Add(locsizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.TOP, LAYOUT_MARGIN)
            locsizer.Add(dummy)
            locsizer.Add(label, 0, wx.LEFT, LAYOUT_MARGIN)

        return label

    # ----------------------------------------------------------------------------
    # wxProgressDialog operations
    # ----------------------------------------------------------------------------

    def Update(self, *args):
        """ Update the progress dialog with a (optionally) new message. """
        for i, v in enumerate(args):
            if v:
                try:
                    nmin = v[4]
                    if nmin is not None:
                        self.CGProgress[i].min = nmin
                except:
                    pass
                try:
                    nmax = v[3]
                    if nmax is not None:
                        self.CGProgress[i].max = nmax
                except:
                    pass
                val = v[0]
                self.CGProgress[i].position = val
                try:
                    newmsg = v[1]
                    if newmsg and newmsg != self.Msgs[i].GetLabel():
                        self.Msgs[i].SetLabel(newmsg)
                        # wx.YieldIfNeeded()
                except:
                    pass
                try:
                    newlabel = v[2]
                    if newlabel:
                        self.CGProgress[i].SetText(newlabel)
                except:
                    pass
        # self.OnTimer(None) #update the elapsed and check for button click
        return self._state != Canceled

    def OnTimer(self, event):
        if self._elapsed:
            elapsed = time.time() - self._timeStart
            if self._last_timeupdate < elapsed:
                self._last_timeupdate = elapsed

            self.SetTimeLabel(elapsed, self._elapsed)

        if self._state == Finished:

            if not self._windowStyle & wx.PD_AUTO_HIDE:

                self.EnableClose()

                if newmsg == "":
                    # also provide the finishing message if the application didn't
                    self.Msgs[i].SetLabel("Done.")

                # wx.YieldIfNeeded()
                self.ShowModal()
                return False

            else:
                # reenable other windows before hiding this one because otherwise
                # Windows wouldn't give the focus back to the window which had
                # been previously focused because it would still be disabled
                self.ReenableOtherWindows()
                self.Hide()

        # we have to yield because not only we want to update the display but
        # also to process the clicks on the cancel and skip buttons
        wx.YieldIfNeeded()

        return self._state != Canceled

    def SetupProgressBar(self, prog, mmin, mmax, text="asis"):
        if mmin != mmax:
            if text != "asis":
                prog.SetText(text)
            prog.min = mmin
            prog.max = mmax
            prog.position = mmin  # ---------------------------------------------------------------------------- #

    def ShowDialog(self, show=True):
        """ Show the dialog. """

        # reenable other windows before hiding this one because otherwise
        # Windows wouldn't give the focus back to the window which had
        # been previously focused because it would still be disabled
        if not show:
            self.ReenableOtherWindows()

        return self.Show()

    # ----------------------------------------------------------------------------
    # event handlers
    # ----------------------------------------------------------------------------

    def OnCancel(self, event):
        """ Handles the wx.EVT_BUTTON event for the Cancel button. """

        if self._state == Finished:

            # this means that the count down is already finished and we're being
            # shown as a modal dialog - so just let the default handler do the job
            event.Skip()

        else:

            # request to cancel was received, the next time Update() is called we
            # will handle it
            self._state = Canceled

            # update the buttons state immediately so that the user knows that the
            # request has been noticed
            self.DisableAbort()

            # save the time when the dialog was stopped
            self._timeStop = time.time()

        self.ReenableOtherWindows()

    def OnDestroy(self, event):
        """ Handles the wx.EVT_WINDOW_DESTROY event for PyProgress. """

        self.ReenableOtherWindows()
        event.Skip()

    def OnClose(self, event):
        """ Handles the wx.EVT_CLOSE event for PyProgress. """

        if self._state == Uncancelable:

            # can't close this dialog
            event.Veto()

        elif self._state == Finished:

            # let the default handler close the window as we already terminated
            self.Hide()
            event.Skip()

        else:

            # next Update() will notice it
            self._state = Canceled
            self.DisableAbort()

            self._timeStop = time.time()

    def ReenableOtherWindows(self):
        """ Re-enables the other windows if using wx.WindowDisabler. """

        if self._windowStyle & wx.PD_APP_MODAL:
            if hasattr(self, "_winDisabler"):
                del self._winDisabler

        else:

            if self._parentTop:
                self._parentTop.Enable()

    def SetTimeLabel(self, val, label=None):
        """ Sets the elapsed time label. """

        if label:

            hours = val / 3600
            minutes = (val % 3600) / 60
            seconds = val % 60
            strs = ("%lu:%02lu:%02lu") % (hours, minutes, seconds)

            if strs != label.GetLabel():
                label.SetLabel(strs)

    def EnableAbort(self, enable=True):
        """ Enables or disables the Cancel button. """

        if self._hasAbortButton:
            if self._btnAbort:
                self._btnAbort.Enable(enable)

    def EnableClose(self, enable=True):
        """ Enables or disables the Close button. """

        if self._hasAbortButton:
            if self._btnAbort:
                self._btnAbort.Enable(enable)
                self._btnAbort.SetLabel("Close")
                self._btnAbort.Bind(wx.EVT_BUTTON, self.OnClose)

    def DisableAbort(self):
        """ Disables the Cancel button. """

        self.EnableAbort(False)
