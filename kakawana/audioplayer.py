# -*- coding: utf-8 -*-

import sys, os
from PyQt4 import QtCore, QtGui, uic
from PyQt4.phonon import Phonon

class AudioPlayer(QtGui.QWidget):
    def __init__(self, url, parent = None):

        self.url = url
        
        QtGui.QWidget.__init__(self, parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Preferred)
        
        self.player = Phonon.createPlayer(Phonon.MusicCategory,
             Phonon.MediaSource(url))
        self.player.setTickInterval(100)
        self.player.tick.connect(self.tock)
        
        self.slider = Phonon.SeekSlider(self.player , self)
        
        self.status = QtGui.QLabel(self)
        self.status.setAlignment(QtCore.Qt.AlignRight |
            QtCore.Qt.AlignVCenter)
    
        self.download = QtGui.QPushButton("Download", self)
        self.download.clicked.connect(self.fetch)
        
        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.status)
        layout.addWidget(self.download)
        
        self.player.play()

    def tock(self, time):
        time = time/1000
        h = time/3600
        m = (time-3600*h) / 60
        s = (time-3600*h-m*60)
        self.status.setText('%02d:%02d:%02d'%(h,m,s))

    def fetch(self):
        print 'Should download %s'%self.url

def main():
    app = QtGui.QApplication(sys.argv)
    window=AudioPlayer(sys.argv[1])
    window.show()
    # It's exec_ because exec is a reserved word in Python
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
