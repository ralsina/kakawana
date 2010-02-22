# -*- coding: utf-8 -*-

"""A simple backend for kakawana, using Elixir"""

import os
from elixir import *

dbdir=os.path.join(os.path.expanduser("~"),".kakawana")
dbfile=os.path.join(dbdir,"kakawana.sqlite")

# It's good policy to have your app use a hidden folder in 
# the user's home to store its files. That way, you can 
# always find them, and the user knows where everything is.

class Feed(Entity):
    """
    A comic book feed
    """
    
    # By inheriting Entity, we are using Elixir to make this 
    # class persistent, Task objects can easily be stored in 
    # our database, and you can search for them, change them, 
    # delete them, etc.        
    
    using_options(tablename='feeds')
    # This specifies the table name we will use in the database, 
    # I think it's nicer than the automatic names Elixir uses.
    name = Field(Unicode,required=True)
    '''The name of the comic'''
    url = Field(Unicode,required=True)
    '''The URL of the comic's website'''
    xmlurl = Field(Unicode,required=True)
    '''The URL for the RSS/Atom feed'''
    lastUpdate = Field(DateTime,default=None,required=False)
    '''Last time this feed was downloaded'''
    data=Field(Unicode,required=True)
    
    def __repr__(self):
        return "Feed: "+self.url
        
    # It's always nicer if objects know how to turn themselves 
    # into strings. That way you can help debug your program 
    # just by printing them. Here, our groceries task would 
    # print as "Task: Buy groceries".
    
# Since earlier I mentioned Tags, we need to define them too:

class Tag(Entity):
    """
    A tag we can apply to a feed or post.
    """
    # Again, they go in the database, so they are an Entity.
    
    using_options(tablename='tags')
    name = Field(Unicode,required=True)
    feeds = ManyToMany("Feed")
    #posts = ManyToMany("Post")
    
    def __repr__(self):
        return "Tag: "+self.name

# Using a database involves a few chores. I put them 
# in the initDB function. Just remember to call it before 
# trying to use Tasks or Tags!

def initDB():
    # Make sure ~/.pyqtodo exists
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
        