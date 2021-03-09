import wx
import wx.combo
import time
class WrappedListCtrl(wx.VListBox):

    def __init__(self, parent, ):

        # Since we are using multiple inheritance, and don't know yet
        # which window is to be the parent, we'll do 2-phase create of
        # the ListCtrl instead, and call its Create method later in
        # our Create method.  (See Create below.)
        wx.VListBox.__init__(self, parent,
                           style=wx.LC_SINGLE_SEL|wx.NO_BORDER)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        wx.EVT_PAINT(self, self.OnPaint)
        # self.PostCreate(wx.PreVListBox())

        self.value = -1
        self.curitem = -1
        self.itemList = []
        self.original_strings_list = []

    def OnDraw(self, event=None):
        wx.VListBox.OnDraw(self)

    def OnPaint(self, event=None):
        self.AdjustStrings()
        event.Skip()

    def OnDrawItem(self, dc, rect, n):
        # print "OnDrawItem %s %s %s %s" % (rect, self.GetSelection(), self.GetItemText(n), n)
        gc = wx.GraphicsContext.Create(dc)
        if self.curitem == n:
            pass
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            c = self.GetForegroundColour()

            #b = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            dc.SetTextBackground("Blue")
            c = "Blue"
            gc.SetFont(self.GetFont().Bold(), c)
            #c = self.GetForegroundColour()
        else:
            c = self.GetForegroundColour()
            #b = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            #dc.SetTextBackground(b)
            gc.SetFont(self.GetFont(), c)
        dc.SetTextForeground(c)

        #gc.DrawLabel(str(c)+str(time.time())+self.GetItemText(n), rect,
        #             wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        txt = self.GetItemText(n)
        gc.DrawText(txt, rect[0] + 2, rect[1] + 2)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        #print "OnMeasureItem"
        height = 0
        for line in self.GetItemText(n).split('\n'):
            w, h = self.GetTextExtent(line)
            height += h
        return height + 5


    def AddItem(self, txt):
        self.InsertItem(self.GetItemCount(), txt)

    def InsertItem(self, index, item):
        self.original_strings_list.insert(index, item)
        self.itemList.insert(index, item)
        self.SetItemCount(len(self.itemList))
        self.Refresh()

    def AppendItem(self, item):
        self.original_strings_list.append(item)
        self.itemList.append(item)
        self.SetItemCount(len(self.itemList))
        self.Refresh()

    def OnMotion(self, evt):
        #print evt.GetPosition()
        item = self.HitTest(evt.GetPosition())
        if item >= 0 and item!=self.curitem:
            # self.SetSelection(item)
            self.curitem = item
            self.RefreshAll()
        # evt.Skip()

    def GetItemCount(self):
        return len(self.itemList)

    def OnGetItem(self, n):
        return self.itemList[n]

    def OnLeftDown(self, evt):
        self.value = self.curitem
        # self.Dismiss()
        # evt.Skip()
        # evt = wx.EVT_LISTBOX(attr1="hello", attr2=654)
        evt = wx.CommandEvent(wx.EVT_LISTBOX.evtType[0], self.GetId())
        evt.SetInt(self.value)
        wx.PostEvent(self, evt)

    def GetItemText(self, n):
        return self.OnGetItem(n)

    def SetItemText(self, n, val):
        self.itemList[n]=val

    def FindItem(self, val):
        try:
            return self.itemList.index(val)
        except ValueError:
            return wx.NOT_FOUND

    # Called just prior to displaying the popup, you can use it to
    # 'select' the current item.
    def SetStringValue(self, val):

        idx = self.FindItem(val)
        if idx != wx.NOT_FOUND:
            self.SetSelection(idx)

    # Return a string representation of the current item.
    def GetStringValue(self):
        # print "GetStringValue"
        if self.value >= 0:
            return self.original_strings_list[self.value]
        return ""


    # Return the widget that is to be used for the popup
    def GetControl(self):
        #print "ListCtrlComboPopup.GetControl"
        return self

    # Return final size of popup. Called on every popup, just prior to OnPopup.
    # minWidth = preferred minimum width for window
    # prefHeight = preferred height. Only applies if > 0,
    # maxHeight = max height for window, as limited by screen size
    #   and should only be rounded down, if necessary.
    def AdjustStrings(self):
        dc = wx.ClientDC(self)
        w, h = self.GetSize()
        w-=wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        for i in range(self.GetItemCount()):
            #reset newlines
            text = self.GetItemText(i).replace("\n", "")
            #idealw, idealh, lineh = dc.GetMultiLineTextExtent(text)
            idealw, idealh = dc.GetTextExtent(text)
            #print "idealh", idealh
            #print "idealw", idealw
            #print "w", w
            curW = idealw
            fractionIndex=0
            while curW>w:
                #print "adding newline"
                #print "idealw", idealw
                lenFraction = float(w)/idealw
                fractionIndex = int(lenFraction*len(text)) + fractionIndex
                text = "%s\n%s" % (text[:fractionIndex], text[fractionIndex:] )
                curW-=w
            self.SetItemText(i, text)



class TestTransientPopup(wx.PopupTransientWindow):
    """Adds a bit of text and mouse movement to the wx.PopupWindow"""
    def __init__(self, parent, style):
        wx.PopupTransientWindow.__init__(self, parent, style)

        sizer = wx.BoxSizer(wx.VERTICAL)
        tp = self.listctrl = WrappedListCtrl(self)
        sizer.Add(self.listctrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

        sizer.Fit(self)
        self.Layout()

    def OnSelect(self, event):
        event.Skip()
        # print(self.popupCtrl.value)
        # print(self.popupCtrl.GetStringValue())
        self.Dismiss()

    def OnDismiss(self):
        pass



class myFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "myFrame")
        self.panel = wx.Panel(self, -1)
        self.btn = wx.Button(self.panel, -1, "Stock              Text")
        self.Bind(wx.EVT_BUTTON, self.OnClick, id=self.btn.GetId())

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.txtbox = wx.TextCtrl(self.panel)
        sizer.Add(self.btn, 0, wx.EXPAND)
        sizer.Add(self.txtbox, 0, wx.EXPAND)
        self.listbox = tp = WrappedListCtrl(self.panel)
        tp.InsertItem(tp.GetItemCount(), "First\nItem")
        tp.InsertItem(tp.GetItemCount(), "Second Item")
        tp.InsertItem(tp.GetItemCount(), "Third Item")
        for x in range(75):
            x = str(x)*x
            tp.AppendItem("Item-%s" % x)

        sizer.Add(tp, 1, wx.EXPAND)
        self.Bind(wx.EVT_LISTBOX, self.OnSelectList, id=tp.GetId())
        # self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnSelect, id=tp.GetId())
        self.panel.SetSizer(sizer)
    def OnSelectList(self, event):
        print(("selected", event.GetSelection()))
        print((self.listbox.value))
        print((self.listbox.GetStringValue()))
        event.Skip()

    def OnSelect(self, event):
        # print("selected", event.GetSelection())
        # print(self.tp.listctrl.value)
        print((self.tp.listctrl.EstimateTotalHeight()))
        self.txtbox.SetValue(self.tp.listctrl.GetStringValue())
        self.tp.Dismiss()

    def OnClick(self, evt):
        self.tp = tp = TestTransientPopup(self, wx.SIMPLE_BORDER)
        self.Bind(wx.EVT_LISTBOX, self.OnSelect, id=tp.listctrl.GetId())
        print((self.tp.listctrl.EstimateTotalHeight()))
        tp.listctrl.InsertItem(tp.listctrl.GetItemCount(), "First\nItem")
        tp.listctrl.InsertItem(tp.listctrl.GetItemCount(), "Second Item")
        tp.listctrl.InsertItem(tp.listctrl.GetItemCount(), "Third Item")
        for x in range(75):
            x = str(x)*x
            tp.listctrl.AppendItem("Item-%s" % x)
        # Show the popup right below or above the button
        # depending on available screen space...
        # btn = event.GetEventObject()
        pos = self.btn.ClientToScreen( (0,0) )
        sz = self.btn.GetSize()
        popup_size = tp.GetSize()
        tp.SetSize([sz[0], 400])
        print((self.tp.listctrl.EstimateTotalHeight()))
        tp.listctrl.AdjustStrings()
        print((self.tp.listctrl.EstimateTotalHeight()))
        # tp.listctrl.SetSize([sz[0], 400])
        tp.Refresh()
        tp.listctrl.RefreshAll()
        tp.GetSize()
        tp.Position(pos, (0, sz[1]))  # this puts the popup at the lower left of the multilinetext box  (doesn't control size of popup, just position)


        tp.Popup()
        print((self.tp.listctrl.EstimateTotalHeight()))
        # print(tp.ClientToScreen( (0,0) ))
        # print("popup", tp.listctrl.ClientToScreen( (0,0) ))
        # self.SetValue("Used the popup")


if __name__=="__main__":
    a = wx.App(0)
    f = myFrame()
    f.Show()
    a.MainLoop()