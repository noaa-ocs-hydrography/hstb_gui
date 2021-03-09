import wx
import wx.combo
class ListCtrlComboPopup(wx.VListBox, wx.combo.ComboPopup):

    def __init__(self):
        
            
        
        # Since we are using multiple inheritance, and don't know yet
        # which window is to be the parent, we'll do 2-phase create of
        # the ListCtrl instead, and call its Create method later in
        # our Create method.  (See Create below.)
        self.PostCreate(wx.PreVListBox())

        # Also init the ComboPopup base class.
        wx.combo.ComboPopup.__init__(self)
        
        self.itemList = []



    def OnDrawItem(self, dc, rect, n):
        # print "OnDrawItem %s %s %s %s" % (rect, self.GetSelection(), self.GetItemText(n), n)
        if self.GetSelection() == n:
            pass
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            c = self.GetForegroundColour()

            #b = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            dc.SetTextBackground("Blue")
            #c = self.GetForegroundColour()
        else:
            c = self.GetForegroundColour()
            #b = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            #dc.SetTextBackground(b)
        dc.SetFont(self.GetFont())
        dc.SetTextForeground(c)

        dc.DrawLabel(self.GetItemText(n), rect,
                     wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

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
        self.itemList.insert(index, item)
        self.SetItemCount(len(self.itemList))
        self.Refresh()

    def AppendItem(self, item):
        self.itemList.append(item)
        self.SetItemCount(len(self.itemList))
        self.Refresh()

    def OnMotion(self, evt):
        #print evt.GetPosition()
        item = self.HitTest(evt.GetPosition())
        if item >= 0:
            self.SetSelection(item)
            self.curitem = item

    def OnLeftDown(self, evt):
        self.value = self.curitem
        self.Dismiss()

    def GetItemCount(self):
        return len(self.itemList)

    def OnGetItem(self, n):
        return self.itemList[n]
        """
    def OnMotion(self, evt):
        print self.HitTest(evt.GetPosition())
        item, flags = self.HitTest(evt.GetPosition())
        if item >= 0:
            self.Select(item)
            self.curitem = item
        evt.Skip()
        """
    def OnLeftDown(self, evt):
        self.value = self.curitem
        self.Dismiss()
        evt.Skip()

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
            return self.GetItemText(self.value)
        return ""


    # The following methods are those that are overridable from the
    # ComboPopup base class.  Most of them are not required, but all
    # are shown here for demonstration purposes.


    # This is called immediately after construction finishes.  You can
    # use self.GetCombo if needed to get to the ComboCtrl instance.
    def Init(self):
        
        self.value = -1
        self.curitem = -1


    # Create the popup child control.  Return true for success.
    def Create(self, parent):
        # print "ListCtrlComboPopup.Create"
        wx.VListBox.Create(self, parent,
                           style=wx.LC_SINGLE_SEL|wx.NO_BORDER)
        #self.InsertColumn(0,""
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        return True


    # Return the widget that is to be used for the popup
    def GetControl(self):
        #print "ListCtrlComboPopup.GetControl"
        return self



    # Called immediately after the popup is shown
    def OnPopup(self):
        # print "ListCtrlComboPopup.OnPopup"
        wx.combo.ComboPopup.OnPopup(self)

    # Called when popup is dismissed
    def OnDismiss(self):
        # print "ListCtrlComboPopup.OnDismiss"
        wx.combo.ComboPopup.OnDismiss(self)

    # This is called to custom paint in the combo control itself
    # (ie. not the popup).  Default implementation draws value as
    # string.
    def PaintComboControl(self, dc, rect):
        # print "ListCtrlComboPopup.PaintComboControl"
        wx.combo.ComboPopup.PaintComboControl(self, dc, rect)

    # Receives key events from the parent ComboCtrl.  Events not
    # handled should be skipped, as usual.
    def OnComboKeyEvent(self, event):
        # print "ListCtrlComboPopup.OnComboKeyEvent"
        wx.combo.ComboPopup.OnComboKeyEvent(self, event)

    # Implement if you need to support special action when user
    # double-clicks on the parent wxComboCtrl.
    def OnComboDoubleClick(self):
        # print "ListCtrlComboPopup.OnComboDoubleClick"
        wx.combo.ComboPopup.OnComboDoubleClick(self)

    # Return final size of popup. Called on every popup, just prior to OnPopup.
    # minWidth = preferred minimum width for window
    # prefHeight = preferred height. Only applies if > 0,
    # maxHeight = max height for window, as limited by screen size
    #   and should only be rounded down, if necessary.
    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        # print "ListCtrlComboPopup.GetAdjustedSize: %d, %d, %d" % (minWidth, prefHeight, maxHeight)
        dc = wx.ClientDC(self)
        w, h = wx.combo.ComboPopup.GetAdjustedSize(self, minWidth, prefHeight, maxHeight)
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

        return wx.combo.ComboPopup.GetAdjustedSize(self, minWidth, prefHeight, maxHeight)

    # Return true if you want delay the call to Create until the popup
    # is shown for the first time. It is more efficient, but note that
    # it is often more convenient to have the control created
    # immediately.    
    # Default returns false.
    def LazyCreate(self):
        # print "ListCtrlComboPopup.LazyCreate"
        return wx.combo.ComboPopup.LazyCreate(self)
        



class myFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "myFrame")
        self.panel = wx.Panel(self, -1)
        comboCtrl = wx.combo.ComboCtrl(self.panel, wx.ID_ANY, "")
        print("1")
        popupCtrl = ListCtrlComboPopup()
        print("2")
        # It is important to call SetPopupControl() as soon as possible
        comboCtrl.SetPopupControl(popupCtrl)
        print("here ")
        # Populate using wx.ListView methods
        print(popupCtrl.GetItemCount())
        #popupCtrl.InsertItem(popupCtrl.GetItemCount(), "First Item"
        popupCtrl.InsertItem(popupCtrl.GetItemCount(), "First Item")
        popupCtrl.InsertItem(popupCtrl.GetItemCount(), "Second Item")
        popupCtrl.InsertItem(popupCtrl.GetItemCount(), "Third Item")
        for x in range(75):
            x=str(x)*x
            popupCtrl.AppendItem("Item-%s" % x)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(comboCtrl, 0, wx.EXPAND)
        self.panel.SetSizer(sizer)

if __name__=="__main__":
    a = wx.App(0)
    f = myFrame()
    f.Show()
    a.MainLoop()