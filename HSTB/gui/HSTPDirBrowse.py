import wx
import wx.lib.filebrowsebutton as filebrowse

class HSTP_DirBrowseButton(filebrowse.DirBrowseButton):
    '''The wx lib filebrowsebutton doesn't change the startdirectory when the user changes the 
    directory value, so it doesn't open where you might think -- this is more natural
    ''' 
    def __init__(self, *args, **kyargs):
        try: 
            self.origCallback = kyargs['changeCallback']
        except:
            self.origCallback = lambda x:x
        kyargs['changeCallback']=self.OnMyChanged
        filebrowse.DirBrowseButton.__init__(self, *args, **kyargs)
    def OnMyChanged(self, event):
        self.startDirectory = self.GetValue()
        self.origCallback(event)
