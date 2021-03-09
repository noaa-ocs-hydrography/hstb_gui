from string import capitalize,upper,lower

import wx
import string

from HSTB.shared import Constants
INFINITY = Constants.INFINITY()


class TextCtrlNumValidator(wx.PyValidator):
    def __init__(self, min=-INFINITY, max=INFINITY, flag=None, maxchars=None, msg=''):
        wx.PyValidator.__init__(self)
        self.flag = flag
        self.msg=msg
        self.maxchars = maxchars
        self.SetMinMax(min,max)
        if maxchars:
            if maxchars<1: self.maxchars = None
        wx.EVT_CHAR(self, self.OnChar)
        
    def Clone(self):
        return TextCtrlNumValidator(self.min, self.max, self.flag, self.maxchars, self.msg)
        
    def TransferToWindow(self): # Dialogs automatically call wx.Window.TransferDataToWindow which calls wx.Validator.TransferDataToWindow
        return True             # (default implementation returns False--this causes "Warning: Could not transfer data to window")
    
    def SetMinMax(self, min=-INFINITY, max=INFINITY):
        self.min = min
        self.max = max
    def GetMinMax(self):
        return self.min, self.max
    def GetFlag(self):
        return self.flag
    def GetMaxChars(self):
        return self.maxchars
    def ErrorText(self, dataTypeStr, min, max):
        '''Create an error description string using the dataTypeStr for the name of the value being checked against min/max'''
        if (-INFINITY < min) and (min < INFINITY) and (-INFINITY < max) and (max < INFINITY):
            errormsg='Enter a %s between %.3f and %.3f.'%(dataTypeStr,min,max)
        elif (-INFINITY < min) and (min < INFINITY):
            errormsg='Enter a %s greater than %.3f.'%(dataTypeStr,min)
        elif (-INFINITY < max) and (max < INFINITY):
            errormsg='Enter a %s less than %.3f.'%(dataTypeStr,max)
        else:
            errormsg= capitalize(dataTypeStr)+' not valid.'
        return errormsg
    def ShowError(self, msg):
        '''Pop up a standard error dialog box'''
        notice = wx.MessageBox(msg,'Error Notice', wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self.GetWindow())
    
    def Validate(self, parent=None, bSilent=False):
        '''Check to see the window control's value meets the validator's guidlines.
        If bSilent is True then an error description string or null string is returned otherwise a
        boolean is returned and messages are shown in a dialog window.'''
        self.compositeError=''
        def BuildOrShowError(err):
            if bSilent: self.compositeError+=err
            else: self.ShowError(err)
            
        try:    # to GetValue from window text entry ctrl to validate
            valstr = str(self.GetWindow().GetValue())
            if not self.msg: self.msg=self.GetWindow().GetName()
        except:
            valstr = ''
        rcode = True
        if valstr:
            if self.flag=='ALPHA_ONLY' or self.flag=='DIGIT_ONLY':
                if self.flag=='ALPHA_ONLY':
                    acceptablechars=string.letters
                else:
                    acceptablechars=string.digits
                for c in valstr:
                    if c not in acceptablechars:
                        BuildOrShowError(self.msg+' has an invalid character')
                        rcode=False
                    if self.maxchars:
                        if len(valstr)!=self.maxchars:
                            BuildOrShowError(self.msg+' needs %d characters'%self.maxchars)
                            rcode=False
            elif (valstr.count('.')<=1) and (valstr.count('-')<=1) and (valstr.count('+')<=1):
                try:
                    valfloat=float(valstr)
                    if (self.max<valfloat):
                        BuildOrShowError(self.ErrorText(self.msg, self.min, self.max))
                        rcode=False
                    elif (valfloat<self.min):
                        BuildOrShowError(self.ErrorText(self.msg, self.min, self.max))
                        rcode = False
                except:
                    BuildOrShowError(self.msg+' was not a number')
                    rcode = False
            else:
                BuildOrShowError(self.msg+' is invalid')
                rcode = False
        else:
            BuildOrShowError(self.msg+' is empty')
            rcode = False
        if self.compositeError: self.compositeError+='\n'
        if bSilent: return self.compositeError #return the error messages to specialized validation calls that didn't want a message popped up.
        else: return rcode #return boolean for stock wx dialog calls to Validate or callers that want immediate popup

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
        elif self.flag == 'ALPHA_ONLY':
            if chr(key) in string.letters: event.Skip()
        elif self.flag == 'DIGIT_ONLY':
            if chr(key) in string.digits: event.Skip()
        elif chr(key) in ('-'+'+'+'.'+string.digits):   # equivalent to, say, 'FLOATINGPT_ONLY'
            event.Skip()
        elif not wx.Validator_IsSilent():
            wx.Bell()
        # Returning without calling event.Skip eats the event before it
        # gets to the text control
        return
