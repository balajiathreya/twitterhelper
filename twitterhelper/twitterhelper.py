from flask import Flask
from datetime import datetime
from datetime import time
import pytz
import urllib2, base64
import credentials, json
import os.path
from flask import g, jsonify
from flask.ext.cors import CORS
from flask import request

TWITTER_APIKEY=credentials.twitterapikey
TWITTER_APISECRET=credentials.twitterapisecret
TWITTER_BEARERTOKEN=credentials.twitterbearertoken
FLICKR_APIKEY=credentials.flickrapikey

app = Flask(__name__)
app.config.from_object(__name__)
cors = CORS(app, resources={r"/gettrending": {"origins": "*"}},
            headers="Content-Type")

@app.route('/')
def hello():
    return "This server is a service. Please use the right path"


# functions for /gettrending
# https://dev.twitter.com/docs/auth/application-only-auth
@app.route("/gettrending")
def gettrending():
    lat =  request.args['lat']
    lon =  request.args['lon']
    woeid = getWOEID(lat,lon)
    bearerToken = getBearerToken()
    authorization = 'Bearer ' + bearerToken
    headers = {'Authorization':authorization}
    url = 'https://api.twitter.com/1.1/trends/place.json?id='+woeid
    print url
    req = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(req)
    data = response.read()   
    return data;


def getWOEID(lat,lon):
    headers = {}
    print('getWOEID '+lat)
    print('getWOEID '+lon)
    url = 'https://api.flickr.com/services/rest/?method=flickr.places.findByLatLon&api_key='+FLICKR_APIKEY+'&lat='+str(lat)+'&lon='+str(lon)+'&format=json&nojsoncallback=1'
    print url;
    req = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(req)
    data = response.read()
    jsonData = json.loads(data)
    woeid = jsonData['places']['place'][0]['woeid']
    return woeid;


def getBearerToken():
    return TWITTER_BEARERTOKEN


# bearer tokens don't change for now - but they may change in the future
def getBearerTokenFromTwitter():
    # construct header first
    basic = base64.b64encode(urllib.quote_plus(TWITTER_APIKEY) + ':' + urllib.quote_plus(TWITTER_APISECRET))
    authorization = 'Basic ' + basic
    contentType = 'application/x-www-form-urlencoded;charset=UTF-8'
    headers = {'Authorization':authorization, 'Content-Type':contentType}
    # body then and make request
    body = 'grant_type=client_credentials'
    url = 'https://api.twitter.com/oauth2/token'
    req = urllib2.Request(url, body, headers)
    response = urllib2.urlopen(req)
    tokenJSON = json.loads(response.read())
    return tokenJSON['access_token']


if __name__ == "__main__":
    app.run(debug=True)
