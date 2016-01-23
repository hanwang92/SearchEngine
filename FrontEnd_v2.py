import bottle
import httplib2
import sqlite3
import time
import urllib2
from bottle import route, run, template, get, post, request, redirect, error
from FrontEndHelperFunctions import *
from math import ceil, floor
from bs4 import BeautifulSoup

from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from beaker.middleware import SessionMiddleware
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

iniTable = '''<table><tr><th align = "left">Search Results</th></tr>'''
endTable = '''</table> </body>'''
endHTML = '''</html> '''

searchBar = '''
        <!DOCTYPE html>
        <html>
        <head>
        <title> Vrisko </title>
        </head>
        <body>
        <h1> Vrisko </h1>
        <form action="/anonymous" method="post">
            Query: <input name="keyword" type="text" />
            <input value="Search" type="submit" />
        </form>
        
        <form action="/lucky" method="post">
            Query: <input name="keyword" type="text" />
            <input value="I Feel Lucky" type="submit" />            
        </form>        
        
        '''


        ###Login button ###
        #<FORM METHOD="LINK" ACTION="http://localhost:8080/login">
        #<INPUT TYPE="submit" VALUE="Login">


#varible definition
dict = {}
_keyword_cache = []

scope = 'https://www.googleapis.com/auth/plus.me https://www.googleapis.com/auth/userinfo.email'
###AWS uri###
#redirect_uri = 'http://ec2-54-164-169-56.compute-1.amazonaws.com:8080/redirect'
redirect_uri = 'http://localhost:8080/redirect'
client_id = '569529233074-a9eq4l7argkbjfv1opcp2kdbf2b2hc2b.apps.googleusercontent.com'
client_secret = 'ugqrZlVwM814f9Rmc5_3UGPZ'

#cache
cache_opts = {
    'cache.type': 'file',
    'cache.data_dir': '/tmp/cache/data',
    'cache.lock_dir': '/tmp/cache/lock'
}

cache = CacheManager(**parse_cache_config_options(cache_opts))

tmpl_cache = cache.get_cache(redirect_uri, type='dbm', expire = 3600)
tmpl_cache.clear()


#configure middleware
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './data',
    'session.auto': True
}

wsgi_app = SessionMiddleware(bottle.app(), session_opts)

@route('/')
def home():
    return template('search_anonymous')

###
@post('/anonymous_loading')
def anonymous_loading():
    
    return template('loadingPage')
    
###
@post('/anonymous')
def anonymous_result():
    keyword = request.forms.get('keyword')
    #get rid of the space at the end of string if any
    word = keyword.rstrip() 
    #get rid of the space at the beginning of string if any    
    word = keyword.lstrip()
    uniqueWords = count_word_produce_table(word)
    #return template('result_anonymous',var1=uniqueWords, var2=keyword)
    redirect('/anonymous/'+ keyword+'/0')
    
@post('/lucky')
def lucky_result():
    keyword = request.forms.get('keyword')
    #get rid of the space at the end of string if any
    word = keyword.rstrip() 
    #get rid of the space at the beginning of string if any    
    word = keyword.lstrip()
    uniqueWords = count_word_produce_table(word)
    #return template('result_anonymous',var1=uniqueWords, var2=keyword)
    redirect('/lucky/'+ keyword+'/0')

@route('/login')
def login():
    session = request.environ.get('beaker.session')
    session.save()
    flow = flow_from_clientsecrets("client_secrets.json", scope = scope, redirect_uri = redirect_uri)
    uri = flow.step1_get_authorize_url()
    bottle.redirect(str(uri))

@route ('/redirect')
def redirect_page():
    global user_email
    global user_name
    global user_image
    
    code = request.query.get('code','')
    if(code == ""):
        redirect('/')
        
    flow = OAuth2WebServerFlow(client_id=client_id, client_secret=client_secret, scope=scope, redirect_uri=redirect_uri)
    credentials = flow.step2_exchange(code)
    token = credentials.id_token['sub']
    http = httplib2.Http()
    http = credentials.authorize(http)
    #Get User email
    users_service = build('oauth2', 'v2', http=http)
    user_document = users_service.userinfo().get().execute()
    user_email = user_document['email']
    
    #Get User Name
    users_service = build('plus', 'v1', http=http)
    profile = users_service.people().get(userId='me').execute()
    user_name = profile['displayName']
    user_image = profile['image']['url']
    
    return template('search', var1=user_email, var2 = user_name, var3 = user_image)

@route('/logout')
def logout():
    bottle.redirect("https://accounts.google.com/logout")
    
@error(404)
def error404(error):
    return '''The Page or file you are looking for do not exist. <br> Please visit <a href="http://ec2-54-84-115-83.compute-1.amazonaws.com:8080/"> Vrisko </a> for a new search.'''

@post('/')
def do_get():
    global dict
    keyword = request.forms.get('keyword')
    #get rid of the space at the end of string if any
    word = keyword.rstrip() 
    #get rid of the space at the beginning of string if any    
    word = keyword.lstrip()
    uniqueWords = count_word_produce_table(word)
    dict = updateHash(dict,uniqueWords)
    #Sort our list by value, most frequent words will show up on top
    var2 = sorted(dict.items(), key=lambda x:x[1],reverse=True)
    #Select the entire list if less than 20, and 20 if more than 20 words
    var2 = var2[ :min(len(sorted(dict.items(), key=lambda x:x[1],reverse=True)),20)]
    return template('result',var1=uniqueWords,var2=var2, var3=user_email, var4 = user_name, var5 = user_image)

@route('/anonymous/<keyword>/<pageid>')
def searchpages(pageid, keyword):

    conn = sqlite3.connect('myTable.db')
    c=conn.cursor()

    #get results from table
    words = keyword.split(" ")
    firstWord = (words[0],)
    naviPage = []
    counter = 0

    c.execute("SELECT DISTINCT DocIndex.url, DocTitle.title FROM Lexicon, DocIndex, DocTitle, InvertedIndex, PageRank WHERE Lexicon.word_id = InvertedIndex.word_id AND InvertedIndex.doc_id = DocIndex.doc_id AND DocTitle.doc_id = DocIndex.doc_id AND InvertedIndex.doc_id=PageRank.doc_id AND Lexicon.word LIKE ? ORDER BY PageRank.rank", firstWord)

    result = c.fetchall()
    print result

    for row in result:
        counter+=1
        if counter%10 == 1:
            naviPage.append("")
        print row    
        #split and display as url
        url = str(row).split("'")
        i = 1
        print url
        print url[1]
        print url[3]
        print counter
        ### takes too long to extract
        #soup = BeautifulSoup(urllib2.urlopen(url[1]))
        #print soup.title.string
        ###
        print int(floor(counter/10))
        naviPage[int(floor((counter-1)/10))] += ('<tr><td>'+ url[3] + "</td></tr>" + '<tr><td><a href="' + url[1] + '" target="_blank">'+ url[1] + "</a></td></tr>")

    if counter == 0:
        return template('error_anonymous',var2=keyword)


    naviBar = "Go to Page:<br>"+"""<table border = "0"><tr>"""
    print (len(naviPage))
    for pagenum in range(0, len(naviPage)):
        #naviBar += '<th><a href= "http://ec2-54-84-115-83.compute-1.amazonaws.com:8080/anonymous/' + keyword + '/' + str(pagenum+0) + '">' + str(pagenum+1) + "<a></th>"
        naviBar += '<th><a href= "http://localhost:8080/anonymous/' + keyword + '/' + str(pagenum+0) + '">' + str(pagenum+1) + "<a></th>"
        

    naviBar += "</tr>"

    if int(pageid) < len(naviPage): 
        return searchBar+ "<br>" +"Searched "+  "'%s'<br><br>%s %s%s<br><br>%s%s" %(keyword, iniTable, naviPage[int(pageid)], endTable, naviBar,endHTML) 

    else:
        redirect('/err')

@route('/lucky/<keyword>/<pageid>')
def searchpages(pageid, keyword):

    conn = sqlite3.connect('myTable.db')
    c=conn.cursor()

    #get results from table
    words = keyword.split(" ")
    firstWord = (words[0],)
    naviPage = []
    counter = 0

    c.execute("SELECT DISTINCT DocIndex.url, DocTitle.title FROM Lexicon, DocIndex, DocTitle, InvertedIndex, PageRank WHERE Lexicon.word_id = InvertedIndex.word_id AND InvertedIndex.doc_id = DocIndex.doc_id AND DocTitle.doc_id = DocIndex.doc_id AND InvertedIndex.doc_id=PageRank.doc_id AND Lexicon.word LIKE ? ORDER BY RANDOM()", firstWord)

    result = c.fetchall()
    print result

    for row in result:
        counter+=1
        if counter%10 == 1:
            naviPage.append("")

        #split and display as url
        url = str(row).split("'")
        print url
        print counter
        print int(floor(counter/10))
        naviPage[int(floor((counter-1)/10))] += ('<tr><td>'+ url[3] + "</td></tr>" + '<tr><td><a href="' + url[1] + '" target="_blank">'+ url[1] + "</a></td></tr>")


    if counter == 0:
        return template('error_anonymous',var2=keyword)


    naviBar = "Go to Page:<br>"+"""<table border = "0"><tr>"""
    print (len(naviPage))
    for pagenum in range(0, len(naviPage)):
        #naviBar += '<th><a href= "http://ec2-54-84-115-83.compute-1.amazonaws.com:8080/lucky/' + keyword + '/' + str(pagenum+0) + '">' + str(pagenum+1) + "<a></th>"
        naviBar += '<th><a href= "http://localhost:8080/lucky/' + keyword + '/' + str(pagenum+0) + '">' + str(pagenum+1) + "<a></th>"
        

    naviBar += "</tr>"

    if int(pageid) < len(naviPage): 
        return searchBar+ "<br>" +"Searched "+  "'%s'<br><br>%s %s%s<br><br>%s%s" %(keyword, iniTable, naviPage[int(pageid)], endTable, naviBar,endHTML) 

    else:
        redirect('/err')

    
###AWS uri###
#run(host="0.0.0.0", port="8080", debug=True, app=wsgi_app)
run(host="localhost", port="8080", debug=True, app=wsgi_app)


