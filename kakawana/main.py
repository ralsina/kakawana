# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os, sys, hashlib, re
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
from audioplayer import AudioPlayer
from videoplayer import VideoPlayer
import libgreader as gr
from reader_client import GoogleReaderClient

def h2t(value):
    "Return the given HTML with all tags stripped."
    return re.sub(r'<[^>]*?>', '', value)

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
                f=feedparser.parse(cmd[1],
                    etag = cmd[2],
                    modified = cmd[3].timetuple())
                if 'bozo_exception' in f:
                    f['bozo_exception'] = None
                fetcher_out.put(['updated',cmd[1],f])
                print 'Done'
        except Exception as e:
            print 'exception in fetcher:', e
            fetcher_out.put(['updated',cmd[1],{}])

# Create a class for our main window
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        # Settings
        self.mode = 0
        self.showAllFeeds = False
        self.showAllPosts = False
        self.keepGoogleSynced = True
        
        self.enclosures = []
        self.feed_properties = None
        # This is always the same
        uifile = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),'main.ui')
        uic.loadUi(uifile, self)
        self.ui = self
        #QtWebKit.QWebSettings.globalSettings().\
            #setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)
        #self.ui.setupUi(self)

        self.enclosureLayout = QtGui.QVBoxLayout(self.enclosureContainer)
        self.enclosureContainer.setLayout(self.enclosureLayout)
        self.enclosureContainer.hide()

        # Smart 'Space' that jumps to next post if needed
        self.addAction(self.ui.actionSpace)

        self.ui.html.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateExternalLinks)
        self.ui.html.page().linkClicked.connect(self.linkClicked)

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
        self.update_timer.start(2000)

        self.scheduled_updates = QtCore.QTimer()
        self.scheduled_updates.timeout.connect(self.updateOneFeed)
        self.scheduled_updates.start(30000)

    def on_actionMark_All_As_Read_triggered(self, b=None):
        '''Mark all visible posts in the current feed as read'''
        if b is not None: return
        print 'Marking feed as Read'
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        if fitem._id in (-1,-2):
            return
        for i in range(fitem.childCount()):
            _id=fitem.child(i)._id
            if _id:
                post = backend.Post.get_by(_id=_id)
                post.read = True
        backend.saveData()
        self.refreshFeeds()

    def linkClicked(self,url):
        if unicode(url.scheme()) == 'cmd':
            # These are fake URLs that trigger kakawana's actions
            cmd = unicode(url.host()).lower()
            print 'COMMAND:', cmd # This is the action name

            # Feed commands
            if cmd == 'mark-all-read':
                print 'Triggering mark-all-read'
                self.ui.actionMark_All_As_Read.trigger()
                
            elif cmd == 'refresh':
                self.updateCurrentFeed()

            # Post commands
            elif cmd == 'keep-unread':
                self.actionKeep_Unread.trigger()
        else:
            QtGui.QDesktopServices.openUrl(url)

    def updateCurrentFeed(self):
        '''Launches a forced update for the current feed'''
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        feed = backend.Feed.get_by(xmlurl = fitem._id)
        if feed:
            print  "Manual update of: ",feed.xmlurl
            fetcher_in.put(['update', feed.xmlurl, feed.etag, feed.check_date])

    def updateOneFeed(self):
        """Launches an update for the feed that needs it most"""
        feed = backend.Feed.query.order_by("check_date").limit(1)[0]
        print feed.check_date
        # Only check if it has not been checked in at least 10 minutes
        if (datetime.datetime.now() - feed.check_date).seconds > 600:
            print  "Scheduled update of: ",feed.xmlurl
            fetcher_in.put(['update', feed.xmlurl, feed.etag, feed.check_date])
        
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
        # FIXME: hide read posts if needed
        for i in range(self.ui.feeds.topLevelItemCount()):
            fitem = self.ui.feeds.topLevelItem(i)
            if fitem._id == feed_id:
                # This is the one to update
                feed = backend.Feed.get_by(xmlurl = feed_id)
                # Get the ids of the existing items
                existing = set()
                for j in range (fitem.childCount()):
                    existing.add(fitem.child(j)._id)
                    
                posts = feed.posts[::-1]
                for post in posts:
                    # If it's not there, add it
                    if post._id not in existing and (
                            post.read == False or self.showAllPosts):
                        pitem=post.createItem(None)
                        fitem.insertChild(0, pitem)
                unread_count = len(filter(lambda p: not p.read, feed.posts))
                fitem.setText(0,'%s (%d)'%(feed.name,unread_count))
                fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
                if self.ui.feeds.currentItem() == fitem or \
                        self.showAllFeeds or \
                        unread_count:
                    fitem.setHidden(False)
                else:
                    fitem.setHidden(True)

    def loadFeeds(self, expandedFeedId=None, currentItemId=None):
        '''Creates all items for feeds and posts.

        If expandedFeedId is set, that feed's item will be expanded.
        if currentItemId is set, that item will be current (FIXME)

        '''
        scrollTo = None
        feeds=backend.Feed.query.order_by('name').all()
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
            scrollTo = fitem
            
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
            fitem=QtGui.QTreeWidgetItem([h2t('%s (%d)'%(feed.name,unread_count))])
            fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
            fitem._id = feed.xmlurl
            self.ui.feeds.addTopLevelItem(fitem)
            if expandedFeedId == feed.xmlurl:
                fitem.setExpanded(True)
                scrollTo = fitem
            if fitem._id == expandedFeedId or \
                    self.showAllFeeds or unread_count:
                fitem.setHidden(False)
            else:
                fitem.setHidden(True)

            for post in feed.posts:
                if post.read == False or self.showAllPosts or \
                        post._id == currentItemId:
                    pitem=post.createItem(fitem)
                    if pitem._id == currentItemId:
                        self.ui.feeds.setCurrentItem(pitem)
                        scrollTo = pitem
        if scrollTo:
            self.ui.feeds.scrollToItem(scrollTo)

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

                content = ''
                if 'content' in data:
                    content = '<hr>'.join([c.value for c in data['content']])
                elif 'summary' in data:
                    content = data['summary']
                elif 'value' in data:
                    content = data['value']
                else:
                    print "Can't find content in this entry"
                    print data

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

            # Enclosures
            for enclosure in self.enclosures:
                enclosure.hide()
                enclosure.deleteLater()
            self.enclosures=[]
            for e in data.enclosures:
                # FIXME: add generic 'download' enclosure widget
                cls = None
                if hasattr(e,'type'):
                    if e.type.startswith('audio'):
                        cls = AudioPlayer
                    elif e.type.startswith('video'):
                        cls = VideoPlayer
                    if cls:
                        player = cls(e.href,
                            self.enclosureContainer)
                        player.show()
                        self.enclosures.append(player)
                        self.enclosureLayout.addWidget(player)
            if self.enclosures:
                self.enclosureContainer.show()
            else:
                self.enclosureContainer.hide()
            
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
            self.updateCurrentFeed()
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
        if len(feeds) > 1:
            items = [ u'%d - %s'%(i,feed['feed']['title']) for i,feed in enumerate(feeds) ]
            ll=QtCore.QStringList()
            for i in items:
                ll.append(QtCore.QString(i))
            item, ok = QtGui.QInputDialog.getItem(self,
                u"Kakawana - New feed",
                u"What feed do you prefer for this site?",
                ll,
                editable = False)
            if not ok:
                return
            # Finally, this is the feed URL
            feed = feeds[items.index(unicode(item))]
        else:
            feed = feeds[0]

        link = url
        if 'link' in feed['feed']:
            self.url = feed['feed']['link']
        elif 'links' in feed['feed'] and feed['feed']['links']:
            self.url = feed['feed']['links'][0].href

        # Add it to the DB
        f=backend.Feed.update_or_create(dict (
                       name = unicode(feed['feed']['title']), 
                       url = unicode(link),
                       xmlurl = unicode(feed['href']),
                       data = unicode(base64.b64encode(pickle.dumps(feed['feed'])))),
                       surrogate = False)
        backend.saveData()
        if self.keepGoogleSynced:
            # Add this feed to google reader
            reader = self.getGoogleReader2()
            if reader:
                reader.subscribe_feed(f.xmlurl, f.name)
        f.addPosts(feed=feed)
        self.loadFeeds(f.xmlurl)

    def modeChange(self, mode=None):
        #if not isinstance(mode, int):
            #return
        self.mode = mode
        print "Switching to mode:", mode
        self.on_feeds_itemClicked(self.ui.feeds.currentItem())

    def on_actionUpdate_Feed_activated(self, b=None):
        if b is not None: return
        self.updateCurrentFeed()

    def refreshFeeds(self):
        '''Like a loadFeeds, but always keeps the current one open'''
        item = self.ui.feeds.currentItem()
        _id = None
        _pid = None
        if item:
            fitem = item.parent()
            _pid = item._id
            if not fitem:
                fitem = item
            _id = fitem._id
        self.loadFeeds(_id, currentItemId = _pid)

    def on_actionEdit_Feed_activated(self, b=None):
        if b is not None: return

        item = self.ui.feeds.currentItem()
        _id = None
        if item:
            fitem = item.parent()
            if not fitem:
                fitem = item
            _id = fitem._id

        feed = backend.Feed.get_by(xmlurl=_id)
        if not feed: # No feed selected
            return

        if not self.feed_properties:
            from feedproperties import Feed_Properties
            self.feed_properties = Feed_Properties()
        self.ui.vsplitter.addWidget(self.feed_properties)

        # get feed and load data into the widget
        self.feed_properties.name.setText(feed.name)
        self.feed_properties.url.setText(feed.url or '')
        self.feed_properties.xmlurl.setText(feed.xmlurl)
        
        self.feed_properties.show()

    def getGoogleReader(self):
        # FIXME: make this part of a prefs dialog or something
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
            return None

        # Do import
        username = unicode(d.username.text())
        password = unicode(d.password.text())
        if d.remember.isChecked():
            # Save in appropiate keyring
            keyring.set_password('kakawana','google_username',username)
            keyring.set_password('kakawana','google_password',password)

        auth = gr.ClientAuth(username, password)
        reader = gr.GoogleReader(auth)
        return reader

    def getGoogleReader2(self):
        # FIXME: make this part of a prefs dialog or something
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
            return None

        # Do import
        username = unicode(d.username.text())
        password = unicode(d.password.text())
        if d.remember.isChecked():
            # Save in appropiate keyring
            keyring.set_password('kakawana','google_username',username)
            keyring.set_password('kakawana','google_password',password)

        reader = GoogleReaderClient(username, password)
        return reader


    def on_actionImport_Google_Reader_activated(self, b=None):
        if b is not None: return
        reader = self.getGoogleReader()
        if not reader: return
        reader.buildSubscriptionList()
        feeds = reader.getFeeds()
        for f in feeds:
            f1 = backend.Feed.update_or_create(dict(name = f.title.decode('utf-8'), xmlurl = f.url),
                surrogate=False)
        backend.saveData()
        self.refreshFeeds()

    def on_actionSync_Google_Feeds_activated(self, b=None):
        if b is not None: return
        reader = self.getGoogleReader()
        if not reader: return
        
        reader.buildSubscriptionList()
        g_feeds = reader.getFeeds()
        # Check what feeds exist in google and not here:
        new_in_google=[]
        for f in g_feeds:
            if not backend.Feed.get_by(xmlurl = f.url):
                new_in_google.append(f.url)
        print 'New in Google:', new_in_google

        # Check what feeds exist here and not in google:
        g_feed_dict={}
        for f in g_feeds:
            g_feed_dict[f.url] = f
        new_here = []
        for f in backend.Feed.query.all():
            if f.xmlurl not in g_feed_dict:
                new_here.append([f.xmlurl, f.name])
        #print 'New here:', new_here
        # FIXME: don't aways do this
        reader = self.getGoogleReader2()
        if reader:
            for xmlurl, name in new_here:
                print 'Adding to google:', name
                reader.subscribe_feed(xmlurl, name)

        # Check what feeds have been deleted here since last sync:

    def on_actionShow_All_Posts_toggled(self, b=None):
        print 'SAP:', b
        self.showAllPosts = b
        self.refreshFeeds()

    def on_actionShow_All_Feeds_toggled(self, b=None):
        print 'SAF:', b 
        self.showAllFeeds = b
        self.refreshFeeds()

    def on_actionSpace_activated(self, b=None):
        '''Scroll down the current post, or jump to the next one'''
        if b is not None: return
        frame = self.html.page().mainFrame()
        if frame.scrollBarMaximum(QtCore.Qt.Vertical) == \
            frame.scrollPosition().y():
                self.on_actionNext_Post_activated()
        else:
            frame.scroll(0,self.html.height())
            
    def on_actionNext_Post_activated(self, b=None):
        '''Jump to the beginning of the next post'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if not item:
            item = self.ui.feeds.topLevelItem(0)
        if item:
            item = self.ui.feeds.itemBelow(item)
            self.ui.feeds.setCurrentItem(item)
            self.on_feeds_itemClicked(item)
            
    def on_actionKeep_Unread_activated(self, b=None):
        '''Mark the current post as unread'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if not item.parent(): return # Not a post
        post = backend.Post.get_by(_id = item._id)
        if not post: return
        post.read = False
        backend.saveData()
        self.refreshFeeds()

    def on_actionDelete_Feed_activated(self, b=None):
        '''Unsubscribe from current feed'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if item:
            fitem = item.parent()
            if not fitem:
                fitem = item
            feed = backend.Feed.get_by(xmlurl = fitem._id)
            if not feed: return

            # Got the current feed, now, must delete it
            feed.delete()
            backend.saveData()

            # May need to delete feed from google
            if self.keepGoogleSynced:
                # Add this feed to google reader
                reader = self.getGoogleReader2()
                if reader:
                    reader.unsubscribe_feed(fitem._id)
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
