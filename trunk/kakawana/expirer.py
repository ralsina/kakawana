# -*- coding: utf-8 -*-
'''Script that expires all feeds'''

import backend

def main():
    for f in backend.Feed.query.all():
        print 'Expiring: ', f.xmlurl
        f.expire()

if __name__ == "__main__":
    backend.initDB()
    main()