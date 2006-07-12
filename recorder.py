#!/var/lib/install/usr/bin/python2.4
import alsaaudio, sys, time
from xml.dom.minidom import Document as xmlDocument
import gtk, hildon
import threading, gobject
import gps as gps_sock, socket
import wave

file_prefix = "/media/mmc1/recorder_data/"
gobject.threads_init()

class Recorder(threading.Thread):
  def __init__(self, input):
    self.inp = input
    self.start_time = time.strftime("%Y-%m-%dT%H-%M-%S")
    self.file = file_prefix + ''.join([self.start_time, ".wav"])
    self.newfile = None
    self.recording = True
    self.muted = False
    try:
      self.mic = alsaaudio.Mixer('Mic', 0, 'hw:1')
    except alsaaudio.ALSAAudioError:
      gtk.main_quit()
    self.eos = False
    threading.Thread.__init__(self)
  
  def setFile(self, file):
    if file[-4:] == ".xml":
      file = file[:-4]
    if file[-4:] != ".wav":
      file = file_prefix + ''.join([file,'.wav'])
    self.newfile = file
    print file
  
  def stop(self):
    self.recording = False
  
  def set_eos(self, val):
    if not val and self.muted:
      self.mic.setvolume(100,0,'capture')
    self.eos = val
  
  def run(self):  
    self.mic.setvolume(100,0,'capture')
    self.muted = False
    store = 0
    fd = wave.open(self.file, 'wb')
    fd.setnchannels(1)
    fd.setsampwidth(2)
    fd.setframerate(8000)
    while self.recording:
      l,data = self.inp.read()
      
      if l:
        fd.writeframes(data)
#        store += 1
#      if store == 9 and self.eos:
#        self.muted = True
#        self.mic.setvolume(0,0,'capture')
#      elif store == 19:
#        if self.eos:
#          self.muted = False
#          self.mic.setvolume(100,0,'capture')
#        store = 0
      del data
    
    self.stop_time = time.strftime("%Y-%m-%dT%H-%M-%S")
    fd.close()
    if self.newfile:
      import shutil
      shutil.move(self.file, self.newfile)
      self.file = self.newfile
    

class Uploader(threading.Thread):
  def __init__(self, ui, cmd):
    self.ui = ui
    self.cmd = cmd
    threading.Thread.__init__(self)
  
  def run(self):
    import os
    self.ui.app.modify_bg(gtk.STATE_NORMAL, self.ui.color_upload)
    stdin, stdout = os.popen4(self.cmd)
    if stdout:
      for l in stdout:
        print l
      
    self.ui.app.modify_bg(gtk.STATE_NORMAL, self.ui.color_stop)
  

class Ui:
  def __init__(self, tags=None, server=None, publisher=None):
    self.app = hildon.App()
    self.appview = hildon.AppView("Tagging Recorder")
    
    self.hbox = gtk.HBox(False, 0)
    
    self.vbr = gtk.VBox()  #right side
    self.vbr.set_border_width(10)
    self.vbr.set_spacing(20)
    
    self.vbl = gtk.VButtonBox() #left side
    self.vbr.set_border_width(10)
    self.vbr.set_spacing(20)
    
    self.img_record = gtk.image_new_from_stock(gtk.STOCK_MEDIA_RECORD, \
                                               gtk.ICON_SIZE_BUTTON*2)
    self.img_save = gtk.image_new_from_stock(gtk.STOCK_SAVE_AS, \
                                             gtk.ICON_SIZE_BUTTON*2)
    self.img_upload = gtk.image_new_from_stock(gtk.STOCK_JUMP_TO, \
                                               gtk.ICON_SIZE_BUTTON*2)
    
    self.record_button = gtk.ToggleButton("Record")
    self.record_button.set_property("image", self.img_record)
    self.record_button.connect("toggled", self.record_button_callback)
    
    self.eos = gtk.CheckButton("EOS")
    self.eos.set_active(False)
    self.eos.connect("toggled", self.eos_callback)
    
    #self.tag_button = gtk.Button(None, gtk.STOCK_INDENT)
    self.tag_button = gtk.Button(None, gtk.STOCK_ADD)
    image,label = \
            self.tag_button.get_children()[0].get_children()[0].get_children()
    label.set_text("Create Tag")
    stock,size = image.get_stock()
    image.set_from_stock(stock, size*2)
    self.tag_button.connect("clicked", self.tag_button_callback)
    
    self.file_button = gtk.Button("")
    self.file_button.set_property("image", self.img_save)
    self.file_button.connect("clicked", self.file_button_callback)
    
    self.upload_button = gtk.Button("")
    self.upload_button.set_property("image", self.img_upload)
    self.upload_button.connect("clicked", self.upload_button_callback)
    
    self.upload_server = gtk.Entry()
    if not server:
      self.upload_server.set_text("localhost:")
    
    self.tag_combo = gtk.combo_box_new_text()
    self.tag_combo.connect("changed", self.tag_combo_callback)
    
    if not tags:
      self.tag_checks = [gtk.CheckButton("interruption"), \
                         gtk.CheckButton("applause"), \
                         gtk.CheckButton("laughter"), \
                         gtk.CheckButton("coughing"), \
                         gtk.CheckButton("speaker-change")]


    else:
      self.tag_checks = [gtk.CheckButton(tag) for tag in tags]
    
    self.table_check = gtk.Table(len(self.tag_checks)/2,2,True)
    
    x,y = 0,0
    for check in self.tag_checks:
      self.table_check.attach(check, y, y+1, x, x+1)
      y += 1
      if y == self.table_check.get_property("n-columns"):
        y = 0
        x += 1
    
    #self.tag_update = gtk.Button(None, gtk.STOCK_REFRESH)
    self.tag_update = gtk.Button(None, gtk.STOCK_SAVE)
    image,label = \
            self.tag_update.get_children()[0].get_children()[0].get_children()
    label.set_text("Save Tag")
    stock,size = image.get_stock()
    image.set_from_stock(stock, size*2)
    self.tag_update.connect("clicked", self.tag_update_callback)
    
    self.quit = gtk.Button(None, gtk.STOCK_QUIT)
    self.quit.connect("clicked", self.destroy)
    
    ## Create status label:
    self.statusLabel = gtk.Label("Hello there.")
    self.statusLabel.set_line_wrap(True)
    self.statusLabel.show()
    ## In other parts of the code, use statusLabel like so:
    ## self.statusLabel.set_text("Press Start to begin\nrecording audio.")
    ## self.refresh()

    ## Create gps label:
    self.gpsLabel = gtk.Label("Hello there.")
    self.gpsLabel.set_line_wrap(True)
    self.gpsLabel.show()

    self.color_stop   = gtk.gdk.color_parse("#FFFFFF")
    self.color_record = gtk.gdk.color_parse("#FF0000")
    self.color_upload = gtk.gdk.color_parse("#0000FF")

    # Create Left Pane

    self.vbl.add(self.gpsLabel)
    self.vbl.add(self.record_button)
    self.vbl.add(self.tag_button)
    self.vbl.add(self.tag_update)
    # Hiding EOS button for now. See task #118.
    #    self.vbl.add(self.eos)
    # Hiding file button for now. See task #109, Remove "file" button.
    #    self.vbl.add(self.file_button)
    # Hiding upload button
    #    self.vbl.add(self.upload_button)
    # Hiding upload server
    #    self.vbl.add(self.upload_server)
    self.vbl.add(self.quit)


    # Create Right Pane

    self.vbr.add(self.tag_combo)    
    self.vbr.add(self.statusLabel)
    self.vbr.add(self.table_check)
    
    self.hbox.add(self.vbl)
    self.hbox.add(gtk.VSeparator())
    self.hbox.add(self.vbr)
    
    self.app.set_title("Tagging Recorder")
    self.app.set_two_part_title(False)
    self.app.set_appview(self.appview)
    
    self.appview.connect("destroy", self.destroy)

    gtk.Container.add(self.appview, self.hbox)
    
    
    self.app.show_all()
    
    self.tags = {}
    self.pub = publisher
    self.gpss = {}
    
    self.gps = None
    
    self.r = None

    try:
      self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, \
                             alsaaudio.PCM_NORMAL, "hw:1")
      self.inp.setchannels(1)
      self.inp.setrate(8000)
      self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
      self.inp.setperiodsize(800)   #collect in factors of 1 second chunks
      self.statusLabel.set_text("Microphone detected.\nGood.")
    except:
      self.statusLabel.set_text("COULD NOT FIND MICROPHONE.\n Restart and try again.")

    self.make_data_dir()

  def make_data_dir(self):
    import os
    stdin, stdout = os.popen4("mkdir " + file_prefix)
    return


  def refresh(self):
    while gtk.events_pending():
      gtk.main_iteration()
  
  def init_gps(self):
    self.gpss = {}
    try:
      self.gps = gps_sock.GPS()
      self.gpsLabel.set_text("GPSD detected."); self.refresh()
    except socket.error, (errno, strerror):
      self.gps = None
      self.gpsLabel.set_text("GPSD not detected."); self.refresh()
    
  
  def init_xmlDoc(self):
    self.xmlDoc = xmlDocument()
    sensor_data = self.xmlDoc.createElement('sensor-data')
    sensor_data.setAttribute('version', "1.0")
    self.xmlDoc.appendChild(sensor_data)
    self.publisher = self.xmlDoc.createElement('publisher')
    if self.pub:
      self.publisher.setAttribute('id', self.pub)
    else:
      f = open('/etc/hostname')
      self.publisher.setAttribute('id', f.readline().strip())
      f.close()
    sensor_data.appendChild(self.publisher)
  
  def destroy(self, widget, data=None):
    if self.r:
      self.r.stop()
      time.sleep(.25)
      self.write_xml()
    gtk.main_quit()
    
  
  def record_button_callback(self, widget, data=None):
    if widget.get_active():
      self.tags = {}
      [check.set_active(False) for check in self.tag_checks]
      for ii in range(len(self.tag_combo.get_model())):
        self.tag_combo.remove_text(ii)
      self.init_gps()
      self.r = Recorder(self.inp)
      self.file = file_prefix + ''.join([self.r.start_time, '.xml'])
      self.r.start()
      self.app.modify_bg(gtk.STATE_NORMAL, self.color_record)
      image = self.record_button.get_property("image")
      image.set_from_stock(gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_BUTTON*2)
    else:
      self.app.modify_bg(gtk.STATE_NORMAL, self.color_stop)
      image = self.record_button.get_property("image")
      image.set_from_stock(gtk.STOCK_MEDIA_RECORD, gtk.ICON_SIZE_BUTTON*2)
      if self.r:
        self.r.stop()
        time.sleep(.25)
        self.write_xml()
      self.init_xmlDoc()
    
  
  def write_xml(self):
    sn = self.xmlDoc.createElement('sensor')
    sn.setAttribute('name', "usb microphone")
    sn.setAttribute('type', 'acoustic')
    self.publisher.appendChild(sn)
    ad = self.xmlDoc.createElement('acousic-data')
    ad.setAttribute('start-time', self.r.start_time)
    ad.setAttribute('end-time', self.r.stop_time)
    ad.setAttribute('sample-rate', '8000')
    ad.setAttribute('sample-size-bits', '16')
    ad.setAttribute('channels', '1')
    ad.setAttribute('format', 'WAV')
    ad.setAttribute('encoding', 'PCM')
    file = self.xmlDoc.createTextNode(self.r.file)
    ad.appendChild(file)
    sn.appendChild(ad)
    
    for tag in self.tags:
      t = self.xmlDoc.createElement('tag')
      if self.gpss:
        if self.gpss[tag][0] != "361.0":
          g = self.xmlDoc.createElement('gps-coordinates')
          gt = self.xmlDoc.createTextNode(' '.join(self.gpss[tag]))
          g.appendChild(gt)
          t.appendChild(g)
        
      time = self.xmlDoc.createElement('time')
      stamp = self.xmlDoc.createTextNode(tag)
      time.appendChild(stamp)
      t.appendChild(time)
      types = self.xmlDoc.createElement('types')
      text = []
      ii = 0
      for check in self.tag_checks:
        type = check.get_label()
        if self.tags[tag][ii]:
          text.append(type)
        ii += 1
      if text:
        txt = self.xmlDoc.createTextNode(' '.join(text))
        types.appendChild(txt)
        t.appendChild(types)
      sn.appendChild(t)
    
    #write xml to disk
    fd = open(self.file, 'w')
    self.xmlDoc.writexml(fd, encoding="UTF-8", addindent="  ", newl = '\n')
    fd.close()
  
  def tag_button_callback(self, widget, data=None):
    if self.r:
      if self.r.recording:
        now = time.strftime("%Y-%m-%dT%H-%M-%S")
        val = [False for x in range(len(self.tag_checks))]
        gval = ["361.0", "361.0", "-1.0"]

        if self.gps:
          self.gps.update()
          gval = [str(self.gps.position()[0]), \
                  str(self.gps.position()[1]), \
                  str(self.gps.altitude())]
          
        self.tags[now] = val
        self.gpss[now] = gval
        self.tag_combo.append_text(now)
        self.tag_combo.set_active(len(self.tag_combo.get_model())-1)
        [check.set_active(False) for check in self.tag_checks]
        self.update_gps_status()
        
  def update_gps_status(self):
    gval = [361.0, 361.0, -1.0]
    gerror = ""
    gmode = ""
    gstatus = ""
    gsatellites = ""
    if self.gps:
      self.gps.update()

      try:
        gmode = self.gps.mode(text = True)
        gstatus = self.gps.status(text = True)
        gsatellites = str(self.gps.satellites())
        gerror = str(self.gps.error()[0]) + "m"
        gval = [str(self.gps.position()[0]), \
                str(self.gps.position()[1]), \
                str(self.gps.altitude())]
      except KeyError:
        pass

    self.statusLabel.set_text("GPS Status:" + gstatus + \
                              ",   Mode:" + gmode + \
                              ",   # Sats:" + gsatellites + \
                              '\nLat:' + str(gval[0]) + \
                              '  Lon:' + str(gval[1]) + \
                              '  Alt:'+ str(gval[2]) + 'm' + \
                              '\nAccuracy: ' + gerror)


    self.refresh()
    
  
  def eos_callback(self, widget, data=None):
    if widget.get_active():
      self.r.set_eos(True)
      pass
    else:
      self.r.set_eos(False)
      pass
    
  
  def tag_update_callback(self, widget, data=None):
    #add checked checkboxes to selected tag
    vals = [check.get_active() for check in self.tag_checks]
    self.tags[self.tag_combo.get_active_text()] = vals
  
  def tag_combo_callback(self, widget, data=None):
    vals = self.tags[widget.get_active_text()]
    for ii in range(len(vals)):
      self.tag_checks[ii].set_active(vals[ii])
  
  def file_button_callback(self, widget, data=None):
    if self.r:
      dialog = hildon.FileChooserDialog(self.app, \
                                        gtk.FILE_CHOOSER_ACTION_SAVE)
      #dialog.set_local_only(True)
      
      #dialog.set_file_name(self.file)
      response = dialog.run()
      if response == gtk.RESPONSE_OK:
        f = dialog.get_filename()
        self.r.setFile(f)
        if f[-4:] != '.xml':
          f = ''.join([f, '.xml'])
        self.file = f
        print self.file
      dialog.destroy()
    
  
  def upload_button_callback(self, widget, data=None):
    if self.r:
      if self.r.recording:
        return
      
    dialog = hildon.FileChooserDialog(self.app, \
                                      gtk.FILE_CHOOSER_ACTION_OPEN)
    
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
      text = '/var/lib/install/bin/scp'
      file = ''.join([dialog.get_filename()[:-4], '*'])
      server = self.upload_server.get_text()
      if server[:-1] != ':':
        server = ''.join([server, ':'])
      text = ' '.join([text, file, server])
      up = Uploader(self, text)
      up.start()
    dialog.destroy()
  
  def main(self):
    self.init_xmlDoc()
    gtk.main()
  

if __name__ == "__main__":
  import getopt, sys
  tags = []
  server = ''
  publisher = ''
  opts, args = getopt.getopt(sys.argv[1:], 'f:s:hp:')
  if opts:
    for o,a in opts:
      if o == '-f':
        f = open(a,'r')
        s = f.read()
        tags = [tag for tag in s.split()]
      if o == '-s':
        server = a
      if o == '-p':
        publisher = a
      if o == '-h':
        print \
     """usage: recorder [-f file] [-s server] [-p publisher] [-h] [TAGs ...]
  -f file       file containing whitespace separated tags
                defaults to "interruption", "applause", "laughter", "coughing", "speaker-change"
  -s server     sever to upload files to
                defaults to "localhost"
  -p publisher  id of the publisher
                defaults to the value of /etc/hostname
  -h            displays this message and exits
  TAGs          list of tag types to use inplace of the defaults"""
        sys.exit()
    
  elif args:
    tags = args

  if not tags:
    try:
      f = open("/media/mmc1/TAGS.txt")
      s = f.read()
      tags =  [tag for tag in s.split()]
    except:
      tags = ["calibrated", "repaired", "replaced", "added", "repositioned", "damage-detected", "destroyed", "action-of-note", "diary-notation", "comm-noted", "comment"]

      
  ui = Ui(tags, server, publisher)
  ui.main()
  

