# This includes the two classes RawOpengl and Opengl
#  from OpenGL.TK in the PyOpenGL distribution
# ported to wx.Python by greg Landrum

#builtins
import os,sys
import traceback
import math

#3rd party
import numpy
from PIL import Image # get PIL's functionality...

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import wx
from wx.glcanvas import *

#custom
#from HSTB.shared.Constants import *
from HSTB.shared import CPydroExt

def v3distsq(a,b):
    d = ( a[0] - b[0], a[1] - b[1], a[2] - b[2] )
    return d[0]*d[0] + d[1]*d[1] + d[2]*d[2]


class QUAD_STRIP:
    @staticmethod
    def __enter__():
        glBegin(GL_QUAD_STRIP)
    @staticmethod
    def __exit__(*args):
        glEnd()
    
class GLBEGIN:
    def __init__(self, glcommand):
        self.glcommand = glcommand
    def __enter__(self):
        glBegin(self.glcommand)
    @staticmethod
    def __exit__(*args):
        glEnd()

class PushedGLMatrix:
    def __init__(self):
        pass
    def __enter__(self):
        glPushMatrix()
    @staticmethod
    def __exit__(*args):
        glPopMatrix()

class PushedGLAttribs:
    def __init__(self, glattribs):
        self.glattribs = glattribs
    def __enter__(self):
        glPushAttrib(self.glattribs)
    @staticmethod
    def __exit__(*args):
        glPopAttrib()

class PushedGLLighting(PushedGLAttribs):
    def __init__(self, extra_attribs=0):
        PushedGLAttribs.__init__(self, GL_LIGHTING_BIT|extra_attribs)    

''' #example usage
  with QUAD_STRIP:
      glColor3f(1.0,1.0,1.0) #corner 1
      glNormal3f(0.57735027, 0.57735027, 0.57735027)
      glVertex3f(0.5, 0.5, 0.5)
      glColor3f(1.0,0.0,1.0) #corner 2
      glNormal3f(0.57735027, -0.57735027, 0.57735027)
      glVertex3f(0.5, -0.5, 0.5)
      ....

  with GLBase.GLBEGIN(GL_LINES):
      #glBegin(GL_LINES)
      for r in range(0, 150, 10):
          for c in range(0,150,10):
              glVertex3f(r, 0, 0)
              glVertex3f(r,150,0)
              glVertex3f(0,r,0)
              glVertex3f(150,r,0)
      #glEnd()
'''


if OpenGL.__version__!='1.5.6b1':
    def glTranslateScene(s, x, y, mousex, mousey):
        #glMatrixMode(GL_MODELVIEW)
        #mat = glGetDoublev(GL_MODELVIEW_MATRIX)
        glMatrixMode(GL_PROJECTION)
        mat = glGetDoublev(GL_PROJECTION_MATRIX)
        glLoadIdentity()
        glTranslatef(s * (x - mousex), s * (mousey - y), 0.0)
        glMultMatrixd(mat)

    def glRotateScene(s, xcenter, ycenter, zcenter, x, y, mousex, mousey):
        #glMatrixMode(GL_MODELVIEW)
        #mat = glGetDoublev(GL_MODELVIEW_MATRIX)
        glMatrixMode(GL_PROJECTION)
        mat = glGetDoublev(GL_PROJECTION_MATRIX)
        glLoadIdentity()
        glTranslatef(xcenter, ycenter, zcenter)
        glRotatef(s * (y - mousey), 1., 0., 0.)
        glRotatef(s * (x - mousex), 0., 1., 0.)
        glTranslatef(-xcenter, -ycenter, -zcenter)
        glMultMatrixd(mat)

#a global holder to share glLists thru.   glSharedListsDict={share_key:[[canvase1, canvase2], [list1, list2, list3]]}
class glListSharer(dict):
  CANVASES=0; LISTS=1
  #def __del__(self):
    #print 'delinting glListShare'
  def addList(self, share_key, DispList):
    canvases, displists = self.setdefault(share_key, [[],[]])
    displists.append(DispList)
    self[share_key]=[canvases, displists]
  def addCanvas(self, share_key, canv):
    '''If s52 module is loaded it will override this function'''
    canvases, displists = self.setdefault(share_key, [[],[]])
    if len(canvases)>0:
      CPydroExt.GLShareLists(canvases[0], canv)
    canvases.append(canv)
    self[share_key]=[canvases, displists]
    
  def removeList(self, share_key, disp):
    canvases, displists = self[share_key]
    displists.remove(disp)
    self[share_key]=[canvases, displists]

  def removeCanvas(self, share_key, canv):
    canvases, displists = self[share_key]
    canvases.remove(canv)
    self[share_key]=[canvases, displists]
    # free any associated display lists before deleting the contexts (not sure this needs to be done as GL porbably cleans this up automatically on destruction
    if len(canvases)==0:
      for DL in displists:
        DL.ClearAll()
    
glSharedListsDict=glListSharer()
class GLNamedTexture:
  def __init__(self):
    self.texName=glGenTextures(1)
    self.Activate()
  def __del__(self):
    glDeleteTextures([self.texName])
  def Activate(self):
    glBindTexture(GL_TEXTURE_2D, self.texName) #activates the texture -- any glTexImage call after this will load a texture and any polygons will have texture drawn on them
  def Deactivate(self):
    glBindTexture(GL_TEXTURE_2D, 0) #set to default texture so the named one doesn't get overwritten accidently
    
class GLDisplayLists:
  '''This class contains and manages the openGL display list numbers used in glCallList.
  They need a container class since they must be deallocated when finished.
  They are stored as lists in a dictionary.
  '''
  def __init__(self, nShare=1):
    self.display_lists={'nothing':[]}
    self.default='nothing'
    self.nShare=nShare
    if self.nShare: glSharedListsDict.addList(self.nShare, self)
  def __del__(self):
    self.ClearAll()
    #the global glSharedListsDict object is getting garbage collected before the canvas/display list on shutdown - so make sure the object still exists
    if glSharedListsDict and self.nShare: glSharedListsDict.removeList(self.nShare, self)
    #dmem('del %s'%self.__class__.__name__)
    
  def ClearAll(self):
      '''Use this function to clear all display lists related to an object - good for closing/loading a pss '''
      for k in list(self.display_lists.keys()):
          self.Clear(k)
  def ClearBranch(self, disp_key):
      '''Since the GLContexts aren't sharing properly yet we're abusing GL and making a display list for each window
      where the key is the operation followed by the string representation of the window handle.  This necessitates a
      funtion to clear, say, all the depth lists at once.'''
      for k in list(self.display_lists.keys()):
        if disp_key in k:
          self.Clear(k)
    
  def Clear(self, disp_key):
      '''Clear a particular display list.
      Good for when the underlying data changes and the display must be modified.
      E.g. excessing would cause depth mesh to change but not features or TCARI. '''
      L=self.display_lists.setdefault(disp_key, []) #the list to clear
      for n in L: #free any old glCallLists
          #print 'delete glList', disp_key, n
          glDeleteLists(n, 1)
      self.display_lists[disp_key]=[] #start with an empty display list
  def AddList(self, disp_key='', mode=GL_COMPILE_AND_EXECUTE):
    if not disp_key: disp_key=self.default
    v=glGenLists(1)
    if v<=0: raise Exception('glGenList failed')
    self.Add(v, disp_key)#make a list of setup commands 
    glNewList(v, mode)
      
  def Add(self, v, disp_key=''):
    if not disp_key: disp_key=self.default
    L=self.display_lists.setdefault(disp_key, []) 
    L.append(v)
  def Get(self, disp_key=''):
    if not disp_key: disp_key=self.default
    return self.display_lists.setdefault(disp_key, [])
  def Draw(self, disp_key=''):
    if not disp_key: disp_key=self.default
    L=self.display_lists.setdefault(disp_key, []) 
    for n in L:
      glCallList(n)
  def SetDefault(self, disp_key):
    self.default=disp_key
  def GetDefault(self, disp_key):
    return self.default
  def Count(self, disp_key=''):
    return len(self.Get(disp_key))
  def CountAll(self):
    return sum([len(v) for v in self.display_lists.values()])

class RawOpengl(GLCanvas):
  def __init__(self, parent, nShare=1): #,*args,**kw):
    '''nShare is a key value that if it evaluates true (not zero, None, "" etc) that it shares glLists
    with any other RawOpengl canvases having the same key.  If it evaluates False then it won't share with any canvas.
    If sharing is specified but there is only one window then it should behave as if not sharing but any canvas added
    later should have access to any display lists already created.'''
    #apply(.GLCanvas.__init__,(self,parent),kw)
    self.ContextNumber, self.DCNumber= None, None
    self.nShare=nShare
    #print "error rawopengl init",glGetError()
    GLCanvas.__init__(self, parent,-1)
    self.context = GLContext(self)
    #print "error rawopengl init",glGetError()
    #wx.EVT_SIZE(self,self.OnSize)  #this was causing onsize to be called twice.  May be overridding base class problem or because of the newer Bind function.
    wx.EVT_PAINT(self,self.OnRedraw)
    wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
    self.bRedrawOnSize=True
  def NoRedrawOnSize(self):
    self.bRedrawOnSize=False
  def DoRedrawOnSize(self):
    self.bRedrawOnSize=True
    
  def OnSize(self, event):
    ### Size callback
    size = self.GetClientSize()
    if self.GetParent().IsShown() and self.context:
      self.SetCurrent()
      glViewport(0, 0, size.width, size.height)
      if self.bRedrawOnSize: self.OnRedraw(event)
      #print size
  def SetCurrent(self):
    #overriding this function because calling setcurrent while building a GLList seems to break the List from storing properly
    #Calling wglGetCurrentXXXX in the DLLs to confirm that the current DC and context is this window and if not then performing SetCurrent
    if self.ContextNumber!=CPydroExt.GLCurrentContext() or self.DCNumber!=CPydroExt.GLCurrentDC():
      GLCanvas.SetCurrent(self, self.context)
      #print 'did set current'
    #else: print 'no set current - yeah!'
    if self.ContextNumber==None or self.DCNumber==None:
      self.ContextNumber=CPydroExt.GLCurrentContext()
      self.DCNumber=CPydroExt.GLCurrentDC()
      if self.nShare: glSharedListsDict.addCanvas(self.nShare, self.ContextNumber)
        
  def __del__(self):
    try:
      #the global glSharedListsDict object is getting garbage collected before the canvas/display list on shutdown - so make sure the object still exists
      if self.ContextNumber!=None and glSharedListsDict and self.nShare: glSharedListsDict.removeCanvas(self.nShare,self.ContextNumber)
    except:
      import traceback
      traceback.print_exc()
      
  def OnEraseBackground(self, event):
    pass # Do nothing, to avoid flashing.

  def OnRedraw(self, *dummy):
    _mode = glGetDouble(GL_MATRIX_MODE)
    glMatrixMode(GL_PROJECTION)
    with PushedGLMatrix():
    
        ### Capture rendering context
        dc = wx.PaintDC(self)
        self.SetCurrent()
        
        self._redraw()
        #print "redraw"
        ### Swap buffers
        self.SwapBuffers()
    
        glFlush()

    glMatrixMode(_mode)

  def OnExpose(self, *dummy):
    self.OnRedraw()

class Opengl(RawOpengl):
  """
    wx.Python bindings for an Opengl widget.
  """
  def __init__(self, parent, autospin_allowed=1,**kw):
    """
      Create an opengl widget.
      Arrange for redraws when the window is exposed or when
      it changes size.
    """
    self.bmp=None
    self.in_redraw=False
    self.left_down=False
    self.middle_down=False
    self.right_down=False
    RawOpengl.__init__(*(self, parent), **kw)
    self.initialised = 0
    self.EraseCache()
    self.ll_width=.25
    self.ll_height=.25
    self.parent = parent
    # Current coordinates of the mouse.
    self.xmouse = 0
    self.ymouse = 0

    self.xspin = 0
    self.yspin = 0

    # Where we are centering.
    self.xcenter = 0.0
    self.ycenter = 0.0
    self.zcenter = 0.0

    # The _back color
    self.r_back = 1.00
    self.g_back = 1.00
    self.b_back = 1.00

    #setup the clipping planes for Ortho display
    self.SetClipping(0,20,20,0,0,20)
    
    # Where the eye is
    self.distance = 10.0

    # Field of view in y direction
    self.fovy = 30.0

    # Position of clipping planes.
    self.near = 0.1
    self.far = 1000.0

    # Is the widget allowed to autospin?
    self.autospin_allowed = autospin_allowed

    # Is the widget currently autospinning?
    self.autospin = 0
  
    self.basic_lighting()
    self.initialised = 1
    glutInit()
    
    wx.EVT_SIZE(self,self.OnSize)
    wx.EVT_PAINT(self,self.OnPaint)
    wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
    wx.EVT_MIDDLE_DOWN(self,self.OnMiddleClick)
    wx.EVT_MIDDLE_UP(self,self.OnMiddleUp)
    wx.EVT_MOTION(self,self.OnMouseMotion)
    wx.EVT_IDLE(self,self.OnIdle)
    #wx.EVT_KEY_UP(self, self.OnKeyUp2) # looks like <escape> can only be caught with EVT_KEY_UP

#     if _dHSTP:
#       wx.EVT_LEFT_DOWN(self,self.OnLeftClick)
#       wx.EVT_LEFT_UP(self,self.OnLeftUp)
#       wx.EVT_RIGHT_DOWN(self,self.OnRightClick)
#       wx.EVT_RIGHT_UP(self,self.OnRightUp)
#       #wx.EVT_CHAR(self,self.OnChar)

  def OnIdle(self,event):
    if self.autospin:
      OnWakeUpIdle()
      self.do_AutoSpin(event)
      event.Skip(1)

  def help(self):
    pass

  def SetClipping(self, l,r,b,t,n,f):
    self.leftpos=l    
    self.rightpos=r    
    self.toppos=t    
    self.botpos=b    
    self.nearpos=n    
    self.farpos=f    
  
#  def OnKeyUp2(self,event):
#    print 'char', event.GetKeyCode()
  def OnChar(self,event):
    #print 'char',event.GetKeyCode()
    key = event.GetKeyCode()
    if key == ord('a'):
      self.autospin_allowed = not self.autospin_allowed
      if self.autospin:
        self.autospin = 0
    elif key == ord('q'):
      self.parent.Destroy()
    else: event.Skip()
      
  def OnLeftClick(self,event):
    self.left_down=True
    self.RecordMouse(event)
    self.initLeft = event.GetX(),event.GetY()
  def OnLeftUp(self,event):
    self.left_down=False
    if not event.m_shiftDown:
      self.OnAutoSpin(event)
  def OnMiddleClick(self,event):
    self.RecordMouse(event)
  def OnRightClick(self,event):
    self.RecordMouse(event)
  def OnLeftDrag(self,event):
    self.OnRotate(event)
  def OnMiddleDrag(self,event):
    self.OnTranslate(event)
  def OnRightDrag(self,event):
    self.OnScale(event)
  def OnMiddleUp(self, event):
      self.middle_down=False
      self.OnMiddleDrag(event)
  def OnRightUp(self, event):
      self.right_down=False
      self.OnRightDrag(event)

  def OnMouseMotion(self,event):
    if not event.Dragging():
      return
    if event.MiddleIsDown():
      self.middle_down=event.MiddleIsDown()
      self.OnMiddleDrag(event)
#     elif _dHSTP and event.LeftIsDown():
#       self.OnLeftDrag(event)
#     elif _dHSTP and event.RightIsDown():
#       self.right_down=event.RightIsDown()
#       self.OnRightDrag(event)
      
  def activate(self):
    self.SetCurrent()

  def basic_lighting(self):
    """
      Set up some basic lighting (single infinite light source).

      Also switch on the depth buffer.
    """
   
    self.activate()
    light_position = (1, 1, 1, 0)
    if OpenGL.__version__=='1.5.6b1':
      glLightf(GL_LIGHT0, GL_POSITION, light_position)
    elif OpenGL.__version__=='2.0.0.44':
      glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glDisable(GL_LIGHTING) #Most everything we do is flat - paper like.  Turn lighting on where needed rather than turning off everywhere
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

  def report_opengl_errors(self, message = "OpenGL error:"):
    """Report any opengl errors that occured while drawing."""

    while True:
      err_value = glGetError()
      if not err_value: break     
      print(message, gluErrorString(err_value))

  def set_background(self, r, g, b):
    """Change the background colour of the widget."""

    self.r_back = r
    self.g_back = g
    self.b_back = b

    self.OnRedraw()

  def set_centerpoint(self, x, y, z):
    """Set the new center point for the model.
    This is where we are looking."""

    self.xcenter = x
    self.ycenter = y
    self.zcenter = z

    self.OnRedraw()

  def set_eyepoint(self, distance):
    """Set how far the eye is from the position we are looking."""

    self.distance = distance
    self.OnRedraw()

  def reset(self):
    """Reset rotation matrix for this widget."""

    #glMatrixMode(GL_MODELVIEW);
    glMatrixMode(GL_PROJECTION)
    #mat = glGetDoublev(GL_PROJECTION_MATRIX)
    glLoadIdentity()
    self.OnRedraw()

  def OnHandlePick(self, event):
    """Handle a pick on the scene."""
    pass

  def RecordMouse(self, event):
    """Record the current mouse position."""
    self.xmouse = event.GetX()
    self.ymouse = event.GetY()

  def OnStartRotate(self, event):
    # Switch off any autospinning if it was happening
    self.autospin = 0
    self.RecordMouse(event)
  def Rescale(self, perc, bDraw=True):
    self.ll_width*=perc
    self.ll_height*=perc
    if bDraw: self.OnRedraw()
    
  def OnScale(self, event):
    """Scale the scene.  Achieved by moving the eye position."""
    scale = 1 + 0.01 * (event.GetY() - self.ymouse) #1% per pixel
    if scale<.15: scale=.15 #prevent a negative (flip) or super zoomout
    self.Rescale(scale)
    #self.distance = self.distance * scale
    self.RecordMouse(event)

  def do_AutoSpin(self,event):
    s = 0.5
    self.activate()

    glRotateScene(0.5,
                  self.xcenter, self.ycenter, self.zcenter,
                  self.yspin, self.xspin, 0, 0)
    self.OnRedraw()


  def OnAutoSpin(self, event):
    """Perform autospin of scene."""

    if self.autospin_allowed:
      self.autospin = 1
      self.yspin = .1 * (event.GetX()-self.initLeft[0])
      self.xspin = .1 * (event.GetY()-self.initLeft[1])
      if self.xspin == 0 and self.yspin == 0:
        self.autospin = 0
      else:
        self.do_AutoSpin(event)


  def OnRotate(self, event):
    """Perform rotation of scene."""
    self.activate()
    if not event.m_shiftDown:
      glRotateScene(0.5,
                    self.xcenter, self.ycenter, self.zcenter,
                    event.GetX(), event.GetY(), self.xmouse, self.ymouse)
    else:
      # rotate about z
      sz = self.GetClientSizeTuple()
      sz = (sz[0]/2, sz[1]/2)
      xp = event.GetX()
      yp = event.GetY()
      dy = (self.ymouse-yp)
      dx = (self.xmouse-xp)
      if yp > sz[1]:
        dx = dx * -1
      if xp < sz[0]:
        dy = dy * -1
      d = dx + dy
      #glMatrixMode(GL_MODELVIEW);
      #m = glGetDouble(GL_MODELVIEW_MATRIX)
      glMatrixMode(GL_PROJECTION)
      m = glGetDoublev(GL_PROJECTION_MATRIX)
      glLoadIdentity()
      glTranslatef(self.xcenter,self.ycenter,self.zcenter)
      glRotatef(.5*d,0,0,1.)
      glTranslatef(-self.xcenter,-self.ycenter,-self.zcenter)
      glMultMatrixd(numpy.ravel(m))
      
    self.OnRedraw()
    self.RecordMouse(event)

  def OnTranslate(self, event):
    """Perform translation of scene."""
    #print 'wxtranslate'
    self.activate()
    size = self.GetClientSize()
    w = size.width
    h = size.height

    # Scale mouse translations to object viewplane so object tracks with mouse
    win_height = max( 1,w)
    obj_c      = (self.xcenter, self.ycenter, self.zcenter)
    win        = gluProject( obj_c[0], obj_c[1], obj_c[2] )
    obj        = gluUnProject( win[0], win[1] + 0.5 * win_height, win[2] )
    dist       = math.sqrt( v3distsq( obj, obj_c ) )
    scale      = abs( dist / ( 0.5 * win_height ) )
    if 'look_point' in self.__dict__: #cheap hack to tell if should use PanBy
      ll1=self.DeviceToLatLon(event.GetX(), event.GetY())
      ll2= self.DeviceToLatLon(self.xmouse, self.ymouse)
      self.PanBy(-ll1[0]+ll2[0], ll1[1]-ll2[1])
    glTranslateScene(scale, event.GetX(), event.GetY(), self.xmouse, self.ymouse)
    self.OnRedraw()
    self.RecordMouse(event)

  def OnPaint(self,event=None, *dummy):
    dc = wx.PaintDC(self)
    self.SetCurrent()
    if not self.initialised: return
    self.OnRedraw(event)

  def BeginDraw(self):
    '''Sets the owened OpenGL context as the current target for OpenGL commands'''
    #update the screen already in memory
    self.activate()

  def FlushNoUpdate(self):
    '''Flush the cache without blitting the image'''
    glFlush()				# Tidy up
  def EndDraw(self, bCache=True):
    '''Move the OpenGL screen into the cached bitmap and draw it to screen.
    bCache specifies if the cached pixels are also to be captured at this time.
    If bCache is false then the previous pixels will remain in the cache and RestoreCache could be called 
    to place them into the GL screen.  This provides a way to "animate" or overlay on top of a finished picture.
    E.g. Draw scene, call EndDraw(True) and show the background and store it.  
    Draw overlay, EndDraw(False) to show the modified image.
    Call RestoreCache(), Draw new overlay, EndDraw(False)
    '''
    glFlush()				# Tidy up
    self.bmp = self.GetGLBitmap()
    if bCache:
        self.CachePixels()
    self.BlitRedraw() #draw the new bitmap
    
  def BlitRedraw(self):
    '''Blit the cached bitmap onto the window'''
    #print 'blit' #@todo - reduce the number of blits to remove flicker
    #try: raise 'see who called this'
    #except: traceback.print_exc()
    w,h = self.GetSizeTuple()
    newdc=wx.MemoryDC()
    newdc.SelectObject(self.bmp)
    dc=wx.ClientDC(self)
    dc.Blit(0,0,w,h,newdc,0,0)
    
  def GetViewport(self):
    self.SetCurrent()
    return glGetIntegerv(GL_VIEWPORT)
  def GetGL_PILImage(self):
    view = self.GetViewport()
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    data = glReadPixels( view[0], view[1], view[2], view[3], GL_RGB, GL_UNSIGNED_BYTE) #
    image = Image.fromstring( "RGB", (view[2]-view[0], view[3]-view[1]), data )
    image = image.transpose( Image.FLIP_TOP_BOTTOM)
    return image
  def SaveGLImage(self, filename, format=None):
    self.GetGL_PILImage().save( filename, format )
  def GetGLwxImage(self):
    '''Copy the pixels from the OpenGL context into a wxImage object'''
    #store the image so screen wipes don't cause a full redraw
    #self.SwapBuffers()
    view = self.GetViewport()
    #print view
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    pixels = glReadPixels( view[0], view[1], view[2], view[3], GL_RGB, GL_UNSIGNED_BYTE) #glGetDoublev(OpenGL.GL.GL_CURRENT_RASTER_POSITION)
    img = wx.EmptyImage(view[2]-view[0], view[3]-view[1] )
    img.SetData( pixels )
    return img.Mirror(False)
  def GetGLBitmap(self):
    '''Copy the pixels from the OpenGL context into a wx.Bitmap object (screen blitable)'''
    return wx.BitmapFromImage(self.GetGLwxImage())
  def EraseCache(self):
    self.cacheview = None
    self.pixels = None
  def CachePixels(self):
    self.cacheview = self.GetViewport(); 
    self.pixels = OpenGL.GL.glReadPixels( self.cacheview[0], self.cacheview[1], self.cacheview[2], self.cacheview[3], OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE) #must use RGBA for this to work right -- because of PyOpenGL or how we have the GLContext set up?
  def RestoreCache(self):
    if self.cacheview!=None:
        OpenGL.GL.glWindowPos2dv([0.0, 0.0])
        OpenGL.GL.glDrawPixels( self.cacheview[2], self.cacheview[3], OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, self.pixels); 
        glClear(GL_DEPTH_BUFFER_BIT) #caching the pixels loses the Z value so make sure they don't go back in with a Z value or drawing might go behind the cached pixels and not be seen.   

  def Clear(self):
    # Clear the background and depth buffer.
    glClearColor(self.r_back, self.g_back, self.b_back, 0.)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
  def OnRedraw(self, event=None, bForce=False, viewport=[]):
    """Cause the opengl widget to redraw itself.
    Will store/restore the screen to/from bitmap for speed when the window just gets invalidated and no new drawing is needed.
    If new drawing is needed/requested:
    Calls BeginDraw (which calls SetCurrent) and stores the Projection and ModelView matrices.
    Sets the glViewport and clears the glContext.
    Derived classes should implement a _redraw( ) function to perform drawing.
    """
    #print 'OnRedraw - self.initialised, already in=', self.initialised, self.in_redraw
    
    if self.in_redraw: return #prevent infinite loop
    #If the event is not a resize and nothing forced a refresh
    #a quick draw of the saved bitmap
    if event:
      if event.GetEventType()==wx.wxEVT_SIZE:
        bForce=True
    if (event and not bForce) and self.bmp:  #a window passed over causing invalidate, for example
      #print 'blit'
      self.BlitRedraw()
      return
    else: #called by program or a resize event.
      self.in_redraw=True
      if not self.initialised: return
      self.BeginDraw()
      size = self.GetClientSize()
      glMatrixMode(GL_PROJECTION);
      with PushedGLMatrix():
      
          glMatrixMode(GL_MODELVIEW);
          with PushedGLMatrix():
      
              w = size.width
              h = size.height
              if viewport:
                w=viewport[0]
                h=viewport[1]
                #print 'forced viewport', viewport
              glViewport(0, 0, w, h)
              #print 'error code',glGetError()
          
              self.Clear()  
        
              self._redraw(event)
          
              #glFlush()	# Tidy up
          
              glMatrixMode(GL_MODELVIEW);
          glMatrixMode(GL_PROJECTION);

      self.EndDraw()
      self.in_redraw=False
      #self.SwapBuffers()
    if event: event.Skip()

  def OnExpose(self, *dummy):
    """Redraw the widget.
    Make it active, update tk events, call redraw procedure and
    swap the buffers.  Note: swapbuffers is clever enough to
    only swap double buffered visuals."""

    self.activate()
    if not self.initialised:
      self.basic_lighting()
      self.initialised = 1
    self.OnRedraw()


  def OnPrint(self, file):
    """Turn the current scene into PostScript via the feedback buffer."""
    self.activate()


    
if __name__ == '__main__':
  #import drawcube
  def DrawSquare(self, o=None):
      # draw six faces of a cube
      glLight(GL_LIGHT0, GL_AMBIENT, [1.0, 1.0, 1.0, 1.0])
      glLight(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
      glLight(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
      glLight(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0]);   
      glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [1.0, 1.0, 1.0, 1.0])
      glMaterial(GL_FRONT, GL_AMBIENT, [1.0, 1.0, 1.0, 1.0])
      glMaterial(GL_FRONT, GL_DIFFUSE, [0.0, 0.0, 0.0, 1.0])
      glMaterial(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
      glMaterial(GL_FRONT, GL_SHININESS, 0.0)
      glColorMaterial(GL_FRONT, GL_AMBIENT) # set which properties track the current color
      glEnable(GL_COLOR_MATERIAL) #enable materials to track the current color
      glBegin(GL_QUADS)
      
      glNormal3f( 0.0, 0.0, 1.0)
      r,g,b=1.0,0.0,0.0
      glColor4f(r, g, b,1.0) # set the current color
      glVertex3f( 0, 0, 0)
      glVertex3f( 0, 1, 0)
      glVertex3f( 1, 1,0)
      glVertex3f( 1, 0, 0)
      
      glEnd()
      glDisable(GL_COLOR_MATERIAL)
  class MyApp(wx.App):
    def OnInit(self):
      frame = wx.Frame(None, -1, "wx.Python Context", wx.DefaultPosition, wx.Size(300,300))
      win = Opengl(frame,autospin_allowed=0)
      win.redraw = DrawSquare
      frame.Show(True)
      self.SetTopWindow(frame)
      return True
  app = MyApp(0)
  app.MainLoop()

