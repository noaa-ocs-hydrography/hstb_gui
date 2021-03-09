import wx

from HSTB.shared.RegistryHelpers import GetFilenameFromUser


def SavePDFReportDoc(doc, pdffilename, reportDirKey, parentwin):
    bTryagain,bUnsaved = True,True
    while bTryagain:
        try:
            doc.canv.save()
            bTryagain,bUnsaved = False,False
        except IOError:
            wx.MessageBox("IOError after building PDF document.  Ensure the \n"+
                          "target path is not read-only.  Also, check that \n"+
                          "the document you are trying to (re)create is not \n"+
                          "open in another application, e.g., Adobe Acrobat"+chr(174)+". \n"+
                          "\n"+
                          "Choose a new filename/path for the PDF document or \n"+
                          "otherwise resolve the file write permission issue \n"+
                          "in using the current filename/path.",
                          'Error Saving PDF Report', wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, parentwin)
            rcode,pdffilename = GetFilenameFromUser(parentwin, RegistryKey=reportDirKey, DefaultVal=os.path.dirname(pdffilename), Title="Save PDF Report Document", DefaultFile=os.path.basename(pdffilename), fFilter="Adobe PDF Files (*.pdf)|*.pdf")
            if rcode==wx.ID_OK:
                doc.canv._filename = pdffilename
            else:
                confirm = wx.MessageBox("Your PDF report has not been saved. \n"+
                                        "Are you sure you want to quit? \n"+
                                        "Choose 'Yes' to abandon the document. \n"+
                                        "Choose 'No' to try again. ",
                                        'Abandon PDF Report?', wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION, parentwin)
                bTryagain = confirm==wx.NO
    return bUnsaved,pdffilename

