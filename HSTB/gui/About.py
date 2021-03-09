import platform
import sys
import wx
import wx.html

from HSTB.shared import Constants


class MyAboutBox(wx.Dialog):
    text = '''
<html>
<body bgcolor="#AC76DE">
<center><table bgcolor="#458154" width="100%%" cellspacing="0"
cellpadding="0" border="1">
<tr>
    <td align="center">
    <h1>Pydro %s</h1><br>
    Updated through %s<br>
    Last Revisions Made: %s<br>
    From URL:  %s<br>
    Running on %s Python %s / wx.Python %s<br>
    </td>
</tr>
</table>
</center>

<p><b>Pydro</b> is a special-purpose hydrographic GIS written by HSTP<em>[1]</em> that
provides important functionality for the quality control of NOAA hydrographic
survey data.  <b>Pydro</b> assists the hydrographer and cartographer in
managing feature/object data in the context of other supporting/correlating
data; i.e., "other" vector data, bathymetry, and raster data.  In addition
to supporting the field- and office-wise survey production processes, <b>Pydro</b>
facilitates research and development efforts into new analysis functions and
procedures.  Using <b>Pydro</b>, critical functionality can be rapidly developed
and delivered to the field--and serve to demonstrate new ideas to industry for
possible integration into commercial off-the-shelf software.</p>

<p>Various extension packages are used in <b>Pydro</b>, including the HSTP
C++ modules <em>PyPeekXTF</em> and <em>PyMidTierPeek</em>, which are statically
linked to the Caris HIPS I/O libraries.  GUI functionality is
based upon wx.Widgets/wx.Windows and wx.Python.  Win32 support is
courteous of the Python Win32Extension module.  Primary support
for raster and vector datasets is provided by the open source
GIS binary kit <em>FWTools</em>; additional geographic coordinate
support is provided by <em>GEOTRANS</em></p>

<center>
<p><b>Python</b>, Copyright (c) 1991-1995 Stichting Mathematisch
Centrum, Amsterdam; Copyright (c) 1995-2000 Corportation for
National Research Initiatives; Copyright (c) 2000 BeOpen.com;
Copyright (c) 2001- Python Software Foundation, all rights reserved</p>

<p><b>wx.Widgets</b> Copyright (c) 1992-2002 Julian Smart, Robert Roebling,
Vadim Zeitlin and other members of the wx.Widgets team, portions
Copyright (c) 1996 Artificial Intelligence Applications Institute</p>

<p><b>wx.Python</b> Robin Dunn and Total Control Software, Copyright (c) 1997-2003.</p>
</center>

<p>Portions of this computer program are Copyright (c) Frank Warmerdam, and
Copyright (c) 1995-2004 LizardTech, Inc. All rights reserved.  MrSID is protected
by U.S. Patent No. 5,710,835. Foreign Patents Pending.<.p>

<p><em>[1]</em> - Pydro developers:  Jack L. Riley and Barry J. Gallagher</p>

<p>Donald Fagen on Pydro:<br>
"A just machine to make big decisions<br>
Programmed by fellows with compassion and vision<br>
We'll be clean when their work is done<br>
We'll be eternally free yes and eternally young"<br>
(actually, lyrics from I.G.Y.)</p>

<center>
<p><wxp class="wx.Button">
    <param name="label" value="OK">
    <param name="id"    value="wx.ID_OK">
</wxp><br></p>
</center>
</body>
</html>
'''

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'About Pydro',)
        html = wx.html.HtmlWindow(self, -1, size=(480, 500))
        pydro_version = str(Constants.PydroVersion())
        rev = Constants.PydroMinorVersion()
        rev_time = Constants.PydroMinorVersionTime()
        url = Constants.PydroSVN_URL()
        plat_machine = platform.machine()
        py_version = sys.version.split()[0]
        wxwin_version = wx.__version__
        html.SetPage(self.text % (pydro_version, rev, rev_time, url, plat_machine, py_version, wxwin_version))
        ir = html.GetInternalRepresentation()
        html.SetSize((ir.GetWidth() + 5, ir.GetHeight() + 5))
        w, h = html.GetSizeTuple()
        self.SetClientSize(wx.Size(w, min(h, 515)))
        self.CentreOnParent(wx.BOTH)
