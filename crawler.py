
# Copyright (C) 2011 by Peter Goodman
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import urllib2
import urlparse
from BeautifulSoup import *
from collections import defaultdict
import re
import sqlite3 as lite
import PageRank

### UnitTest Enclosed In Below ###

import unittest

class TestStringMethods(unittest.TestCase):
    
    def test_Lexicon(self):
    #Check if the word 'engineering' exists
        myConnection = lite.connect("myTable.db")
        self.dataBaseConnection = myConnection
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.execute( """SELECT word FROM Lexicon WHERE word='engineering';""" )
        myresult = self.cursor.fetchall()
        self.assertEqual([('engineering',)],myresult)
        
    def test_DocIndex(self):
    #Check the number and names of urls
        myConnection = lite.connect("myTable.db")
        self.dataBaseConnection = myConnection
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.execute( """SELECT * FROM DocIndex""" )
        myresult = self.cursor.fetchall()
        self.assertEqual(set([(6, u'http://www.mapquest.com/maps?address=10+King%27s+College+Road&city=Toronto&state=ON&zipcode=M5S+3G4&country=CA'),
(4, u'http://www.ece.utoronto.ca'),
(11, u'http://www.eecg.toronto.edu/facilities.html'),
(10, u'http://www.eecg.toronto.edu/grads.html'),
(3, u'http://rrs.osm.utoronto.ca/map/f?p=110:1:12476129108393424156'),
(17, u'http://www.ece.utoronto.ca/Graduate_Studies/Admission.htm'),
(15, u'http://www.ece.utoronto.ca/Graduate_Studies/courses/Timetable_and_Catalogues.htm'),
(13, u'http://www.eecg.toronto.edu/tech_reports/index.html'),
(14, u'http://www.eecg.toronto.edu/~exec/thesis_lib/'),
(2, u'http://www.eecg.toronto.edu/Welcome.html'),
(9, u'http://www.eecg.toronto.edu/faculty.html'),
(5, u'http://www.utoronto.ca'),
(18, u'http://www.eecg.toronto.edu/../cider/index.html'),
(19, u'http://www.ece.utoronto.ca/aboutus/dls.htm'),
(1, u'http://www.eecg.toronto.edu/'),
(7, u'http://www.mapquest.com/maps/map.adp?countryid=41&addtohistory=&country=CA&address=10+King%27s+College+Road&city=Toronto&state=ON&zipcode=M5S+3G4&submit=Get+Map'),
(12, u'http://www.eecg.toronto.edu/projects.html'),
(16, u'http://www.eecg.toronto.edu/~exec/student_guide/Main/index.shtml'),
(8, u'http://www.ece.utoronto.ca/research.html')]),set(myresult))
    
    def test_Links1(self):
    #Check the number ids of link relations
        myConnection = lite.connect("myTable.db")
        self.dataBaseConnection = myConnection
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.execute( """SELECT DISTINCT from_url FROM Links""" )
        myresult = self.cursor.fetchall()
        self.assertEqual(set([(1,),(2,),(14,),(13,),(12,),(11,),(10,),(9,),(5,),(4,),(7,),(6,),(16,)]),set(myresult))
        
    def test_Links2(self):
    #Check all pages that link to page 382
        myConnection = lite.connect("myTable.db")
        self.dataBaseConnection = myConnection
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.execute( """SELECT *  FROM Links WHERE to_url=382""" ) 
        myresult = self.cursor.fetchall()
        self.assertEqual([(4, 382)],myresult)
        
    def test_PageRank(self):
    #Check all pages that have same score
        myConnection = lite.connect("myTable.db")
        self.dataBaseConnection = myConnection
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.execute( """SELECT * FROM PageRank WHERE rank in (SELECT rank FROM PageRank GROUP BY rank HAVING COUNT(*)>1);""" )
        myresult = self.cursor.fetchall()
        self.assertEqual([(5,0.0125673858376),(9,0.0125673858376),(11,0.0125673858376),(12,0.0125673858376),(13,0.0125673858376),(14,0.0125673858376)],myresult)
    
    
### UnitTest Enclosed In Above ###


def attr(elem, attr):
    """An html attribute from an html element. E.g. <a href="">, then
    attr(elem, "href") will get the href or an empty string."""
    try:
        return elem[attr]
    except:
        return ""

WORD_SEPARATORS = re.compile(r'\s|\n|\r|\t|[^a-zA-Z0-9\-_]')

class crawler(object):
    """Represents 'Googlebot'. Populates a database by crawling and indexing
    a subset of the Internet.

    This crawler keeps track of font sizes and makes it simpler to manage word
    ids and document ids."""

    def __init__(self, db_conn, url_file):
        """Initialize the crawler with a connection to the database to populate
        and with the file containing the list of seed URLs to begin indexing."""
        self._url_queue = [ ]
        self._doc_id_cache = { }
        self._word_id_cache = { }
        
        # Varibles intitialized which will be used in some of the functions
        # below 
        self._doc_index = {}
        self._lexicon={}
        self._words_in_doc_tup = []
        self.extract_word_id = []
        self.extract_word = []
        self.inverted_doc_list = []
        self.extract_inverted_index = {}
        self.extract_resolved_url = []
        self.resolved_inverted_index = {}
        
        # Initialize the databse
        self.dataBaseConnection = db_conn
        self.cursor = self.dataBaseConnection.cursor()
        self.cursor.executescript(
            """
            DROP TABLE IF EXISTS DocIndex;
            
            DROP TABLE IF EXISTS Lexicon;
            
            DROP TABLE IF EXISTS InvertedIndex;
            
            DROP TABLE IF EXISTS Links;
            
            DROP TABLE IF EXISTS PageRank;
            
            CREATE TABLE IF NOT EXISTS 
            Links(from_url INTEGER, to_url INTEGER);
            
            CREATE TABLE IF NOT EXISTS 
            Lexicon(word_id INTEGER PRIMARY KEY, 
                    word TEXT UNIQUE);
            
            CREATE TABLE IF NOT EXISTS
            InvertedIndex(word_id INTEGER, 
                    doc_id INTEGER);
                    
            CREATE TABLE IF NOT EXISTS 
            PageRank(doc_id INTEGER PRIMARY KEY, rank INTEGER);
                    
            CREATE TABLE IF NOT EXISTS 
            DocIndex(doc_id INTEGER PRIMARY KEY, 
                    url TEXT);""")

        # functions to call when entering and exiting specific tags
        self._enter = defaultdict(lambda *a, **ka: self._visit_ignore)
        self._exit = defaultdict(lambda *a, **ka: self._visit_ignore)

        # add a link to our graph, and indexing info to the related page
        self._enter['a'] = self._visit_a

        # record the currently indexed document's title an increase
        # the font size
        def visit_title(*args, **kargs):
            self._visit_title(*args, **kargs)
            self._increase_font_factor(7)(*args, **kargs)

        # increase the font size when we enter these tags
        self._enter['b'] = self._increase_font_factor(2)
        self._enter['strong'] = self._increase_font_factor(2)
        self._enter['i'] = self._increase_font_factor(1)
        self._enter['em'] = self._increase_font_factor(1)
        self._enter['h1'] = self._increase_font_factor(7)
        self._enter['h2'] = self._increase_font_factor(6)
        self._enter['h3'] = self._increase_font_factor(5)
        self._enter['h4'] = self._increase_font_factor(4)
        self._enter['h5'] = self._increase_font_factor(3)
        self._enter['title'] = visit_title

        # decrease the font size when we exit these tags
        self._exit['b'] = self._increase_font_factor(-2)
        self._exit['strong'] = self._increase_font_factor(-2)
        self._exit['i'] = self._increase_font_factor(-1)
        self._exit['em'] = self._increase_font_factor(-1)
        self._exit['h1'] = self._increase_font_factor(-7)
        self._exit['h2'] = self._increase_font_factor(-6)
        self._exit['h3'] = self._increase_font_factor(-5)
        self._exit['h4'] = self._increase_font_factor(-4)
        self._exit['h5'] = self._increase_font_factor(-3)
        self._exit['title'] = self._increase_font_factor(-7)

        # never go in and parse these tags
        self._ignored_tags = set([
            'meta', 'script', 'link', 'meta', 'embed', 'iframe', 'frame', 
            'noscript', 'object', 'svg', 'canvas', 'applet', 'frameset', 
            'textarea', 'style', 'area', 'map', 'base', 'basefont', 'param',
        ])

        # set of words to ignore
        self._ignored_words = set([
            '', 'the', 'of', 'at', 'on', 'in', 'is', 'it',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
            'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
            'u', 'v', 'w', 'x', 'y', 'z', 'and', 'or'
        ])
        
        # Initialize the varibles that will be passed _insert_document() and
        # _lexicon_insert_word
        self._next_doc_id = 1
        self._next_word_id = 1

        # keep track of some info about the page we are currently parsing
        self._curr_depth = 0
        self._curr_url = ""
        self._curr_doc_id = 0
        self._font_size = 0
        self._curr_words = None

        # get all urls into the queue
        try:
            with open(url_file, 'r') as f:
                for line in f:
                    self._url_queue.append((self._fix_url(line.strip(), ""), 0))
        except IOError:
            pass
    
    def _insert_document(self, url):
        """A function that actually to insert a url into a document db table
        and then returns that newly inserted document's id."""
        ret_id = self._next_doc_id
        self._next_doc_id += 1
        return ret_id
        
    def _lexicon_insert_word(self, word):
        """A function that actually insert a word into the lexicon db table
        and then returns that newly inserted word's id."""
        ret_id = self._next_word_id
        
        #If database is open, insert word id and word into Lexicon table
        if self.dataBaseConnection:
            self.cursor.execute("""INSERT INTO Lexicon VALUES ('%d','%s')"""%(ret_id,word))
            self.dataBaseConnection.commit()
            
        self._next_word_id += 1
        return ret_id 
    
    def word_id(self, word):
        """Get the word id of some specific word."""
        if word in self._word_id_cache:
            return self._word_id_cache[word]
        
        # 1) add the word to the lexicon, if that fails, then the
        #    word is in the lexicon
        # 2) query the lexicon for the id assigned to this word, 
        #    store it in the word id cache, and return the id.
        word_id = self._lexicon_insert_word(word)
        self._lexicon[word_id] = str(word)

        self._word_id_cache[str(word)] = word_id
        return word_id
    
    def document_id(self, url):
        """Get the document id for some url."""
        if url in self._doc_id_cache:
            return self._doc_id_cache[url]
        
        # just like word id cache, but for documents. if the document
        # doesn't exist in the db then only insert the url and leave
        # the rest to their defaults.
        doc_id = self._insert_document(url)
        self._doc_index[doc_id] = str(url)

        self._doc_id_cache[str(url)] = doc_id
        return doc_id
    
    def _fix_url(self, curr_url, rel):
        """Given a url and either something relative to that url or another url,
        get a properly parsed url."""

        rel_l = rel.lower()
        if rel_l.startswith("http://") or rel_l.startswith("https://"):
            curr_url, rel = rel, ""
            
        # compute the new url based on import 
        curr_url = urlparse.urldefrag(curr_url)[0]
        parsed_url = urlparse.urlparse(curr_url)
        return urlparse.urljoin(parsed_url.geturl(), rel)

    def add_link(self, from_doc_id, to_doc_id):
        """Add a link into the database, or increase the number of links between
        two pages in the database."""
        if self.dataBaseConnection:
            self.cursor.execute("""INSERT INTO Links VALUES('%d', '%d');""" %  (from_doc_id, to_doc_id))
            self.dataBaseConnection.commit()
        # TODO

    def _visit_title(self, elem):
        """Called when visiting the <title> tag."""
        title_text = self._text_of(elem).strip()
        print "document title="+ repr(title_text)

        # TODO update document title for document id self._curr_doc_id
    
    def _visit_a(self, elem):
        """Called when visiting <a> tags."""

        dest_url = self._fix_url(self._curr_url, attr(elem,"href"))

        #print "href="+repr(dest_url), \
        #      "title="+repr(attr(elem,"title")), \
        #      "alt="+repr(attr(elem,"alt")), \
        #      "text="+repr(self._text_of(elem))

        # add the just found URL to the url queue
        self._url_queue.append((dest_url, self._curr_depth))
        
        # add a link entry into the database from the current document to the
        # other document
        self.add_link(self._curr_doc_id, self.document_id(dest_url))

        # TODO add title/alt/text to index for destination url
    
    def _add_words_to_document(self):
        # knowing self._curr_doc_id and the list of all words and their
        # font sizes (in self._curr_words), add all the words into the
        # database for this document
        
        # Extract the word_id of each word, font tuple, sort the resulting list
        # and delete the duplicated word_id
        self.extract_word_id = [x[0] for x in self._curr_words]
        self.extract_word_id.sort()
        self.extract_word_id = list(set(self.extract_word_id))
        
        # Initialize counter i used to trace through all word_ids 
        # enclosed in list
        i = 0
        while i < len(self.extract_word_id) :
            
            # Append all the keywords within the url into one list
            self.extract_word.append(self._lexicon[self.extract_word_id[i]])
            
            #If database is open, insert word id and doc id into InvertedIndex table
            if self.dataBaseConnection:
                self.cursor.execute("""INSERT INTO InvertedIndex  VALUES( '%s', '%s');""" %(self.extract_word_id[i], self.document_id(self._curr_url)))
                self.dataBaseConnection.commit()
                
            i+= 1
            
        # Repeatly add the list of keywords with the corresponding doc_id
        # to a new list 
        current_set = [self.document_id(self._curr_url), self.extract_word] 
        self._words_in_doc_tup = self._words_in_doc_tup + current_set
        
        # Intialize the temporary word list again for next url
        self.extract_word = []
        print "    num words="+ str(len(self._curr_words))

    def _increase_font_factor(self, factor):
        """Increade/decrease the current font size."""
        def increase_it(elem):
            self._font_size += factor
        return increase_it
    
    def _visit_ignore(self, elem):
        """Ignore visiting this type of tag"""
        pass

    def _add_text(self, elem):
        """Add some text to the document. This records word ids and word font sizes
        into the self._curr_words list for later processing."""
        words = WORD_SEPARATORS.split(elem.string.lower())
        for word in words:
            word = word.strip()
            if word in self._ignored_words:
                continue
            self._curr_words.append((self.word_id(word), self._font_size))
        
    def _text_of(self, elem):
        """Get the text inside some element without any tags."""
        if isinstance(elem, Tag):
            text = [ ]
            for sub_elem in elem:
                text.append(self._text_of(sub_elem))
            
            return " ".join(text)
        else:
            return elem.string

    def _index_document(self, soup):
        """Traverse the document in depth-first order and call functions when entering
        and leaving tags. When we come accross some text, add it into the index. This
        handles ignoring tags that we have no business looking at."""
        class DummyTag(object):
            next = False
            name = ''
        
        class NextTag(object):
            def __init__(self, obj):
                self.next = obj
        
        tag = soup.html
        stack = [DummyTag(), soup.html]

        while tag and tag.next:
            tag = tag.next

            # html tag
            if isinstance(tag, Tag):

                if tag.parent != stack[-1]:
                    self._exit[stack[-1].name.lower()](stack[-1])
                    stack.pop()

                tag_name = tag.name.lower()

                # ignore this tag and everything in it
                if tag_name in self._ignored_tags:
                    if tag.nextSibling:
                        tag = NextTag(tag.nextSibling)
                    else:
                        self._exit[stack[-1].name.lower()](stack[-1])
                        stack.pop()
                        tag = NextTag(tag.parent.nextSibling)
                    
                    continue
                
                # enter the tag
                self._enter[tag_name](tag)
                stack.append(tag)

            # text (text, cdata, comments, etc.)
            else:
                self._add_text(tag)

    def crawl(self, depth=2, timeout=3):
        """Crawl the web!"""
        seen = set()

        while len(self._url_queue):

            url, depth_ = self._url_queue.pop()

            # skip this url; it's too deep
            if depth_ > depth:
                continue

            doc_id = self.document_id(url)

            # we've already seen this document
            if doc_id in seen:
                continue

            # Mark this document as haven't been visited and store this document and its id to a persistent file 
            seen.add(doc_id) 
            if self.dataBaseConnection:
                self.dataBaseConnection.execute("""INSERT INTO DocIndex VALUES ('%d','%s') """%(doc_id,url))
                self.dataBaseConnection.commit()
                
            socket = None
            try:
                socket = urllib2.urlopen(url, timeout=timeout)
                soup = BeautifulSoup(socket.read())

                self._curr_depth = depth_ + 1
                self._curr_url = url
                self._curr_doc_id = doc_id
                self._font_size = 0
                self._curr_words = [ ]
                self._index_document(soup)
                self._add_words_to_document()
                print "    url="+repr(self._curr_url)

            except Exception as e:
                print e
                pass
            finally:
                if socket:
                    socket.close()
    
    def get_inverted_index(self):
        # Nested loop used below to trace out the desired format output for
        # get_inverted_index()
        
        # Counter used to trace through all lexicon words
        i = 1        
        while i <= len(self._lexicon):
            # Counter used to trace through each document ID's list of keyword
            j = 1
            while j <= len(self._words_in_doc_tup):
                # Counter used to trace through each words enclosed in the
                # current document ID
                k = 0
                while k < len(self._words_in_doc_tup[j]):
                    if self._lexicon[i] == self._words_in_doc_tup[j][k]:
                        # pass in the correct document ID corresponding to the
                        # keyword break the loop when found
                        self.inverted_doc_list.append(self._words_in_doc_tup[j-1])
                        break
                    k += 1
                j += 2
            
            # Repeatly add the set of doc_ids corresponding to word_id into
            # the resulting dictionary
            self.extract_inverted_index[str(i)] = set(self.inverted_doc_list)
            self.inverted_doc_list = []
            i += 1
        
        return self.extract_inverted_index
        
    def get_resolved_inverted_index(self):
        # Nested loop used below to trace out the desired format output for
        # get_resolved_inverted_index()
        
        # Call get_inverted_index() to populate the extract_inverted_index data structure
        self.get_inverted_index()
        
        # Check whether there is data in inverted_index
        if len(self.extract_inverted_index) != 0:
            
            # Counter used to trace through all lexicon words IDs
            i = 1
            while i <= len(self._lexicon):
                j = str(i)
                
                # Extract the list of doc_id corresponding to the word_id from 
                # self.extract_inverted_index()
                extract_resolved_url = list(self.extract_inverted_index[j])
                
                # Counter used to trace through all of the doc_ids in 
                # self._doc_index
                k = 1
                while k <= len(self._doc_index):
                
                    # Counter used to trace through all of the doc_ids in the doc_id 
                    # set() corresponding to the word_id
                    l = 0
                    while l < len(extract_resolved_url):
                        if extract_resolved_url[l] == k:
                            
                            # pass in the correct url name of the website 
                            # corresponding to the doc_id found in the list
                            # and break the loop when found
                            self.extract_resolved_url.append(self._doc_index[k]) 
                            break   
                        l+=1
                    k+=1
                    
                # Repeatly add the set of website urls corresponding to relevant 
                #word into the resulting dictionary
                self.resolved_inverted_index[self._lexicon[i]] = set(self.extract_resolved_url)
                self.extract_resolved_url = []
                i+=1
        
        return self.resolved_inverted_index
    
    def PageRank(self):
        #Specify parameters of Page Rank algorithm  
        iterations = 20
        initial_pr = 1.0
      
        if self.dataBaseConnection.cursor():
        
            #Fetch all links from persistent file, sort them using PageRank and store them into rankedList
            self.cursor.execute('SELECT * FROM Links;')
            myData = self.cursor.fetchall()
            rankedList = PageRank.page_rank(myData, iterations, initial_pr)
            
            for x in rankedList:
                self.cursor.execute( """INSERT OR REPLACE INTO PageRank (doc_id, rank)  VALUES('%s', '%s');""" %  ( x,  rankedList[x]) ) # Use INSERT OR REPLACE to prevent duplicate
                self.dataBaseConnection.commit() 
    
 
if __name__ == "__main__":
            
    # Initialize/Update myTable.db
    from crawler import crawler
    myConnection = lite.connect("myTable.db")
    bot = crawler(myConnection, "urls.txt")
    bot.crawl(depth=1)        
    bot.PageRank()
    
    
    # Run the Unit Test Suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStringMethods)
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    


