# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os, sys, hashlib
from pprint import pprint

# Import Qt modules
from PyQt4 import QtCore, QtGui, QtWebKit, uic

# Import our backend
import backend

import feedfinder
import feedparser
import pickle
import datetime
import time
import base64
import codecs
import keyring
from multiprocessing import Process, Queue

VERSION="0.0.1"

# Templating stuff
import tenjin
# The obvious import doesn't work for complicated reasons ;-)
to_str=tenjin.helpers.to_str
escape=tenjin.helpers.escape
templateEngine=tenjin.Engine()
tmplDir=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
# To convert UTC times (returned by feedparser) to local times
def utc2local(dt):
  return dt-datetime.timedelta(seconds=time.timezone)
def renderTemplate(tname, **context):
  context['to_str']=to_str
  context['escape']=escape
  context['utc2local']=utc2local
  codecs.open('x.html', 'w', 'utf-8').write(templateEngine.render(os.path.join(tmplDir,tname), context))
  return templateEngine.render(os.path.join(tmplDir,tname), context)
# End oftemplating stuff

fetcher_in = Queue()
fetcher_out = Queue()

# Background feed fetcher
def fetcher():
    while True:
        print 'Fetching'
        try:
            cmd = fetcher_in.get(5)
            if cmd[0] == 'update':
                print 'Updating:', cmd[1],'...',
                f=feedparser.parse(cmd[1])
                fetcher_out.put(['updated',cmd[1],f])
                print 'Done'
        except:
            print 'exception in fetcher'

# Create a class for our main window
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.mode = 0
        self.showAllFeeds = False
        # This is always the same
        uifile = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),'main.ui')
        uic.loadUi(uifile, self)
        self.ui = self
        #QtWebKit.QWebSettings.globalSettings().\
            #setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)
        #self.ui.setupUi(self)
        self.loadFeeds(-1)

        self.modes=QtGui.QComboBox()
        self.modes.addItems(["Feed Decides", "Site", "Feed", "Fast Site", "Fast Feed"])
        self.modes.currentIndexChanged.connect(self.modeChange)
        self.ui.toolBar.addWidget(self.modes)

        self.fetcher = Process(target=fetcher)
        self.fetcher.daemon = True
        self.fetcher.start()

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.get_updates)
        self.update_timer.start(5000)

    def get_updates(self):
        try:
            cmd = fetcher_out.get(False) # Don't block
        except:
            return
        if cmd[0] == 'updated':
            xmlurl = cmd[1]
            feed = backend.Feed.get_by(xmlurl = xmlurl)
            if feed:
                feed.addPosts(cmd[2])
                self.updateFeed(xmlurl)

    def updateFeed(self, feed_id):
        # feed_id is a Feed.xmlurl, which is also item._id
        for i in range(self.ui.feeds.topLevelItemCount()):
            fitem = self.ui.feeds.topLevelItem(i)
            if fitem._id == feed_id:
                # This is the one to update
                feed = backend.Feed.get_by(xmlurl = feed_id)
                # Get the ids of the existing items
                existing = set()
                for j in range (fitem.childCount()):
                    existing.add(fitem.child(j)._id)
                for post in feed.posts:
                    # If it's not there, add it
                    if post._id not in existing:
                        pitem=post.createItem(fitem)
                unread_count = len(filter(lambda p: not p.read, feed.posts))
                fitem.setText(0,'%s (%d)'%(feed.name,unread_count))
                fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))

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
            pitem = post.createItem(fitem)

        posts = backend.Post.query.filter(backend.Post.star==True)
        fitem = QtGui.QTreeWidgetItem(["Starred"])
        fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem._id = -2
        self.ui.feeds.addTopLevelItem(fitem)
        if expandedFeedId == -2:
            fitem.setExpanded(True)
            
        for post in posts:
            pitem=post.createItem(fitem)
        
        for feed in feeds:
            unread_count = len(filter(lambda p: not p.read, feed.posts))
            if self.showAllFeeds or unread_count:
                fitem=QtGui.QTreeWidgetItem(['%s (%d)'%(feed.name,unread_count)])
                fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
                fitem._id = feed.xmlurl
                self.ui.feeds.addTopLevelItem(fitem)
                if expandedFeedId == feed.xmlurl:
                    fitem.setExpanded(True)

                for post in feed.posts:
                    pitem=post.createItem(fitem)

    def on_feeds_itemClicked(self, item=None):
        if item is None: return
        fitem = item.parent()
        if fitem: # Post
            p=backend.Post.get_by(_id=item._id)

            # We display differently depending on current mode
            # The modes are:
            # ["Feed Decides", "Site", "Feed", "Fast Site", "Fast Feed"]
            
            # Use feed mode as feed decides for a while
            if self.mode == 0:
                self.mode = 2
            if self.mode == 0:
                # Feed decides
                self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 1:
                # Site mode
                self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 2:
                # Feed mode
                data = pickle.loads(base64.b64decode(p.data))

                if 'content' in data:
                    content = '<hr>'.join([c.value for c in data['content']])
                elif 'summary' in data:
                    content = data['summary']
                elif 'value' in post:
                    content = data['value']

                # Rudimentary NON-html detection
                if not '<' in content:
                    content=escape(content).replace('\n\n', '<p>')
                
                self.ui.html.setHtml(renderTemplate('post.tmpl',
                    post = p,
                    data = data,
                    content = content,
                    cssdir = tmplDir))
            elif self.mode == 3:
                # Fast site mode
                fname = os.path.join(backend.dbdir, 'cache',
                    '%s.jpg'%hashlib.md5(p._id).hexdigest())
                if os.path.exists(fname):
                    self.ui.html.setHtml('''<img src="file://%s" style="max-width:100%%;">'''%fname)
                else:
                    self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 4:
                # Fast Feed mode
                pass
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
            print 'Sending:', ['update',item._id]
            fetcher_in.put(['update',item._id])
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
        self.loadFeeds(f._id)

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
        f = backend.Feed.get_by(name=feed_name)
        f.addPosts()
        self.refreshFeeds()

    def refreshFeeds(self):
        '''Like a loadFeeds, but always keeps the current one open'''
        item = self.ui.feeds.currentItem()
        _id = None
        if item:
            fitem = item.parent()
            if not fitem:
                fitem = item
            _id = fitem._id
        self.loadFeeds(_id)


    def on_actionImport_Google_Reader_activated(self, b=None):
        if b is not None: return
        from google_import import Google_Import

        d = Google_Import(parent = self)
        username = keyring.get_password('kakawana', 'google_username') or ''
        password = keyring.get_password('kakawana', 'google_password') or ''
        
        d.username.setText(username)
        d.password.setText(password)
        if username or password:
            d.remember.setChecked(True)
        
        r = d.exec_()


        if r == QtGui.QDialog.Rejected:
            return
        # Do import

        username = unicode(d.username.text())
        password = unicode(d.password.text())
        if d.remember.isChecked():
            # Save in appropiate keyring
            keyring.set_password('kakawana','google_username',username)
            keyring.set_password('kakawana','google_password',password)
        import libgreader as gr
        
        auth = gr.ClientAuth(username, password)
        reader = gr.GoogleReader(auth)
        reader.buildSubscriptionList()
        feeds = reader.getFeeds()
        for f in feeds:
            f1 = backend.Feed.update_or_create(dict(name = f.title.decode('utf-8'), xmlurl = f.url),
                surrogate=False)
        backend.saveData()
        self.refreshFeeds()

    def on_actionShow_All_Feeds_toggled(self, b=None):
        print 'SAF:', b 
        self.showAllFeeds = b
        self.refreshFeeds()

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
    
