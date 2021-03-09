'''
Events.py
James Hiebert <james.hiebert@noaa.gov>
'''

import wx

myEVT_DATA = wx.NewEventType()
EVT_DATA = wx.PyEventBinder(myEVT_DATA, 1)

myEVT_CHECKLISTBOX = wx.NewEventType()
myEVT_LOG = wx.NewEventType()
EVT_CHECKLISTBOX = wx.PyEventBinder(myEVT_CHECKLISTBOX, 1)
EVT_LOG = wx.PyEventBinder(myEVT_LOG, 1)


class CheckListBoxEvent(wx.PyCommandEvent):
    def __init__(self, id_, number, checked):
        wx.PyCommandEvent.__init__(self, myEVT_CHECKLISTBOX, id_)
        self.number = number
        self.checked = checked


class LogEvent(wx.PyCommandEvent):
    def __init__(self, id_, msg):
        wx.PyCommandEvent.__init__(self, myEVT_LOG, id_)
        self.msg = msg


class DataEvent(wx.PyCommandEvent):
    def __init__(self, id_, data):
        wx.PyCommandEvent.__init__(self, myEVT_DATA, id_)
        self.data = data
