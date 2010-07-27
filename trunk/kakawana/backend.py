# -*- coding: utf-8 -*-

"""A simple backend for kakawana, using Elixir"""
VERSION="0.0.1"

import os
import re
import time
from elixir import *
import feedparser
import pickle, base64
import datetime, time
# Import Qt modules
from PyQt4 import QtCore, QtGui, QtWebKit

feedparser.USER_AGENT = 'Kakawana/%s +http://kakawana.googlecode.com/'%VERSION

if 'KW_DBDIR' in os.environ:
    dbdir=os.environ['KW_DBDIR']
else:
    dbdir=os.path.join(os.path.expanduser("~"),".kakawana")
dbfile=os.path.join(dbdir,"kakawana.sqlite")

def h2t(value):
    "Return the given HTML with all tags stripped."
    return re.sub(r'<[^>]*?>', '', value)

# It's good policy to have your app use a hidden folder in 
# the user's home to store its files. That way, you can 
# always find them, and the user knows where everything is.

class Feed(Entity):
    """
    A comic book feed
    """
    
    # By inheriting Entity, we are using Elixir to make this 
    # class persistent, Feed objects can easily be stored in
    # our database, and you can search for them, change them, 
    # delete them, etc.        
    
    using_options(tablename='feeds')
    # This specifies the table name we will use in the database, 
    # I think it's nicer than the automatic names Elixir uses.
    name = Field(Unicode,required=True)
    '''The name of the comic'''
    url = Field(Unicode,required=False)
    '''The URL of the comic's website'''
    xmlurl = Field(Unicode,required=True, primary_key=True)
    '''The URL for the RSS/Atom feed'''
    data = Field(Unicode,required=False)
    '''everything in the feed'''
    posts = OneToMany("Post", order_by = "-date")
    '''Posts in the feed'''
    etag = Field(Text, default='')
    '''etag of last check'''
    check_date=Field(DateTime, required=False, default=datetime.datetime(1970,1,1))
    '''timestamp of last check'''
    last_status=Field(Integer, required=False, default=0)
    
    def __repr__(self):
        return "Feed: %s <%s>"%(self.name, self.url)

    @classmethod
    def createFromFPData(cls, url, feed):
        '''
        Create a feed in the DB from feedparser data.

        feed is fedparser.parse(url)
        '''
        from pprint import pprint
        
        link = url
        if 'link' in feed['feed']:
            link = feed['feed']['link']
        elif 'links' in feed['feed'] and feed['feed']['links']:
            link = feed['feed']['links'][0].href

        title = u'No Title'
        if 'title' in feed['feed']:
            title = feed['feed']['title']

        # Add it to the DB
        f = Feed.update_or_create(dict (
            name = unicode(title),
            url = unicode(link),
            xmlurl = unicode(url),
            data = unicode(base64.b64encode(pickle.dumps(feed['feed'])))),
            surrogate = False)
        saveData()
        return f


    def addPosts(self, feed=None):
        '''Takes an optional already parsed feed'''
        self.check_date = datetime.datetime.now()
        saveData()
        if feed == None:
            feed=feedparser.parse(self.xmlurl,
                etag = self.etag,
                modified = self.check_date.timetuple())
        elif feed == {}:
            # This was probably a feedparser bug that made the
            # fetcher crash, so don't try to do much, but
            # mark as updated anyway
            saveData()
            return

        # Fill in missing things
        if not self.url:
            if 'link' in feed['feed']:
                self.url = feed['feed']['link']
            elif 'links' in feed['feed'] and feed['feed']['links']:
                self.url = feed['feed']['links'][0].href
        # Keep data fresh
        self.data = unicode(base64.b64encode(pickle.dumps(feed['feed'])))

        if 'status' in feed:
            if feed.status == 304: # No change
                print "Got 304 on feed update"
                saveData()
                return
            elif feed.status == 301: # Permanent redirect
                print "Got 301 on feed update => %s"%feed.href
                self.xmlUrl=feed.href
            elif feed.status == 410: # Feed deleted. FIXME: tell the user and stop trying!
                print "Got 410 on feed update"
                saveData()
                return
            elif feed.status == 404: # Feed gone. FIXME: tell the user and stop trying!
                print "Got 404 on feed update"
                saveData()
                return
        if 'etag' in feed:
            self.etag = feed['etag']

        for post in feed['entries']:
            p=Post.get_or_create(post)
            self.posts.append(p)
        saveData()
        

class Post(Entity):
    '''Everything in the feed'''
    
    using_options(tablename='posts')
    title = Field(Unicode, required=True)
    url = Field(Unicode, required=True)
    read = Field(Boolean, default=False)
    star = Field(Boolean, default=False)
    data=Field(Unicode,required=True)
    _id=Field(Unicode,required=True, primary_key=True)
    feed=ManyToOne("Feed")
    date=Field(DateTime, required=True)

    @classmethod
    def get_or_create(cls, post):
        """Takes a entry as generated by feedparser and returns
        an existing or a new Post object"""
        #from pudb import set_trace; set_trace()

        post_date = time.localtime()
        try:
            post_date = post.published_parsed
        except AttributeError:
            try:
                post_date = post.updated_parsed
            except AttributeError:
                pass
        if not post_date: # Sometimes it comes back None
            post_date = time.localtime()
        data = base64.b64encode(pickle.dumps({}))
        try:
            data = base64.b64encode(pickle.dumps(post))
        except:
            print 'Error pickling post data', post.id

        post_date = datetime.datetime(*post_date[:6])
        p=Post.update_or_create( dict(
            title = post.title,
            url = post.link,
            _id = post.id,
            date = post_date,
            data = data),
            surrogate = False,
            )
        return p

    def createItem(self, fitem):
        pitem=QtGui.QTreeWidgetItem(fitem,[h2t(self.title) or unicode(self.date)])
        if self.read:
            pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("lightgray")))
        else:
            pitem.setForeground(0, QtGui.QBrush(QtGui.QColor("black")))
        pitem._id=self._id
        return pitem
        
    def __repr__(self):
        return "Post: %s"%self.title

class KeyValue(Entity):
    """Useful for storing random stuff on a key/value store like
    if it were a dictionary"""
    key = Field(Unicode,required=True, primary_key=True)
    value = Field(Unicode,required=True)
    timestamp = Field(DateTime, required = True)

class Tag(Entity):
    """
    A tag we can apply to a feed or post.
    """
    # Again, they go in the database, so they are an Entity.
    
    using_options(tablename='tags')
    name = Field(Unicode,required=True)
    feeds = ManyToMany("Feed")
    posts = ManyToMany("Post")
    
    def __repr__(self):
        return "Tag: "+self.name

# Using a database involves a few chores. I put them 
# in the initDB function. Just remember to call it before 
# trying to use Tags, Posts, etc.!

def initDB():
    # Make sure ~/.kakawana exists
    if not os.path.isdir(dbdir):
        os.mkdir(dbdir)
    # Set up the Elixir internal thingamajigs
    metadata.bind = "sqlite:///%s"%dbfile
    setup_all()
    # And if the database doesn't exist: create it.
    if not os.path.exists(dbfile):
        create_all()
        
    # This is so Elixir 0.5.x and 0.6.x work
    # Yes, it's kinda ugly, but needed for Debian 
    # and Ubuntu and other distros.
    
    global saveData
    import elixir
    if elixir.__version__ < "0.6":
        saveData=session.flush
    else:
        saveData=session.commit
        
