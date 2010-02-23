# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os,sys
from pprint import pprint

# Import Qt modules
from PyQt4 import QtCore,QtGui

# Import the compiled UI module
from Ui_main import Ui_MainWindow as MainWindow

# Import our backend
import backend

import feedfinder
import feedparser
import pickle

# Create a class for our main window
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        
        # This is always the same
        self.ui=MainWindow()
        self.ui.setupUi(self)
        self.loadFeeds()

    def loadFeeds(self):
        feeds=backend.Feed.query.all()
        self.ui.feeds.clear()
        for feed in feeds:
            self.ui.feeds.addItem(feed.name)

    def on_actionNew_Feed_triggered(self, b=None):
        '''Ask for site or feed URL and add it to backend'''
        if b is not None: return
        url,r=QtGui.QInputDialog.getText(self, 
            "Kakawana - New feed", 
            "Enter the URL for the site")
        if not r:
            return
        url=unicode(url)
        print url
        feeds=[]
        feedurls=feedfinder.feeds(url)
        for furl in feedurls:
            print furl
            f=feedparser.parse(furl)
            feeds.append(f)            
        items = [ '%d - %s'%(i,feed['feed']['title']) for i,feed in enumerate(feeds) ]
        ll=QtCore.QStringList()
        for i in items:
            ll.append(QtCore.QString(i))
        item, ok = QtGui.QInputDialog.getItem(self, 
            "Kakawana - New feed", 
            "What feed do you prefer for this site?", 
            ll,
            editable=False)
        if not ok:
            return
        # Finally, this is the feed URL
        feed=feeds[items.index(unicode(item))]

        # Add it to the DB
        f=backend.Feed(name = unicode(feed['feed']['title']), 
                       url = unicode(feed['feed']['link']),
                       xmlurl = unicode(feed['href']),
                       data = unicode(pickle.dumps(feed['feed'])))
        f.save()
        backend.saveData()
        self.loadFeeds()

def main():
    # Init the database before doing anything else
    backend.initDB()
    
    app = QtGui.QApplication(sys.argv)
    window=Main()
    window.show()
    # It's exec_ because exec is a reserved word in Python
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()
    
