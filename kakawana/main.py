# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os, sys, hashlib
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

VERSION="0.0.1"

# Create a class for our main window
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.fast_mode = False
        # This is always the same
        self.ui=MainWindow()
        self.ui.setupUi(self)
        self.loadFeeds(-1)

        self.modes=QtGui.QComboBox()
        self.modes.addItems(["Feed Decides", "Site", "Feed", "Fast Site", "Fast Feed"])
        self.modes.currentIndexChanged.connect(self.modeChange)
        self.ui.toolBar.addWidget(self.modes)

    def loadFeeds(self, expandedFeedId=None):
        feeds=backend.Feed.query.all()
        self.ui.feeds.clear()
        # Add "some recent"
        posts =  backend.Post.query.filter(backend.Post.read==False).\
            order_by("date desc").limit(50)
        fitem = QtGui.QTreeWidgetItem(["Recent"])
        fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem._id = -1
        self.ui.feeds.addTopLevelItem(fitem)
        if expandedFeedId == -1:
            fitem.setExpanded(True)
            
        for post in posts:
            pitem=QtGui.QTreeWidgetItem(fitem,[post.title])
            if post.read:
                pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("lightgray")))
            else:
                pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("black")))
            pitem._id=post._id

        posts = backend.Post.query.filter(backend.Post.star==True)
        fitem = QtGui.QTreeWidgetItem(["Starred"])
        fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem._id = -2
        self.ui.feeds.addTopLevelItem(fitem)
        if expandedFeedId == -2:
            fitem.setExpanded(True)
            
        for post in posts:
            pitem=QtGui.QTreeWidgetItem(fitem,[post.title])
            if post.read:
                pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("lightgray")))
            else:
                pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("black")))
            pitem._id=post._id
        
        for feed in feeds:
            unread_count = len(filter(lambda p: not p.read, feed.posts))
            fitem=QtGui.QTreeWidgetItem(['%s (%d)'%(feed.name,unread_count)])
            fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
            fitem._id = feed.xmlurl
            self.ui.feeds.addTopLevelItem(fitem)
            if expandedFeedId == feed.xmlurl:
                fitem.setExpanded(True)
                
            for post in feed.posts:
                pitem=QtGui.QTreeWidgetItem(fitem,[post.title])
                if post.read:
                    pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("lightgray")))
                else:
                    pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("black")))
                pitem._id=post._id

    def on_feeds_itemClicked(self, item=None):
        if item is None: return
        fitem = item.parent()
        if fitem: # Post
            p=backend.Post.get_by(_id=item._id)
            if not self.fast_mode: #Slow mode
                self.ui.html.load(QtCore.QUrl(p.url))
            else:
                fname = os.path.join(backend.dbdir, 'cache',
                    '%s.jpg'%hashlib.md5(p._id).hexdigest())
                if os.path.exists(fname):
                    self.ui.html.setHtml('''<img src="file://%s" style="max-width:100%%;">'''%fname)
                else:
                    self.ui.html.load(QtCore.QUrl(p.url))
            p.read=True
            backend.saveData()
            item.setForeground(0, QtGui.QBrush(QtGui.QColor("lightgray")))

            # Update unread count
            if fitem._id == -1: # Recent
                pass
            elif fitem._id == -2: # Starred
                pass
            else: # Feed
                unread_count = len(filter(lambda p: not p.read, p.feed.posts))
                fitem.setText(0,'%s (%d)'%(p.feed.name,unread_count))
        else: # Feed
            # FIXME: make this update the feed like google reader
            if not item.isExpanded():
                self.ui.feeds.collapseAll()
                item.setExpanded(True)

    def on_actionNew_Feed_triggered(self, b=None):
        '''Ask for site or feed URL and add it to backend'''
        
        # FIXME: this is silly slow and blocking.
        
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
        items = [ u'%d - %s'%(i,feed['feed']['title']) for i,feed in enumerate(feeds) ]
        ll=QtCore.QStringList()
        for i in items:
            ll.append(QtCore.QString(i))
        item, ok = QtGui.QInputDialog.getItem(self, 
            u"Kakawana - New feed", 
            u"What feed do you prefer for this site?", 
            ll,
            editable=False)
        if not ok:
            return
        # Finally, this is the feed URL
        feed=feeds[items.index(unicode(item))]

        # Add it to the DB
        f=backend.Feed.update_or_create(dict (
                       name = unicode(feed['feed']['title']), 
                       url = unicode(feed['feed']['link']),
                       xmlurl = unicode(feed['href']),
                       data = unicode(pickle.dumps(feed['feed']))),
                       surrogate = False)
        backend.saveData()
        f.addPosts(feed=feed)
        self.loadFeeds()

    def modeChange(self, mode=None):
        #if not isinstance(mode, int):
            #return
        self.mode = mode
        print "Switching to mode:", mode
        self.on_feeds_itemClicked(self.ui.feeds.currentItem())

    def on_actionUpdate_Feed_activated(self, b=None):
        if b is not None: return

        # Launch update of current feed
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        if fitem._id in (-1,-2):
            return
        feed_name=' ('.join(unicode(fitem.text(0)).split(' (')[:-1])
        f= backend.Feed.get_by(name=feed_name)
        f.addPosts()
        self.loadFeeds(fitem._id)
        

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
    
