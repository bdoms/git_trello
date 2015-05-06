import json
from urllib import urlencode
from urllib2 import HTTPError, Request, urlopen
import sys


# API example: https://github.com/sarumont/py-trello/blob/master/trello/__init__.py
class Trello(object):

    def __init__(self, api_key, oauth_token, board_id):
        self.api_key = api_key
        self.oauth_token = oauth_token
        self.board_id = board_id
        self.base_url = 'https://api.trello.com/1'

    def getLists(self):
        return self.makeRequest('GET', '/boards/' + self.board_id + '/lists')

    def findList(self, name):
        tlist = None
        lists = self.getLists()
        for l in lists:
            if l['name'] == name:
                tlist = l
                break
        return tlist

    def getCard(self, card_number):
        return self.makeRequest('GET', '/boards/' + self.board_id + '/cards/' + card_number)

    def addComment(self, card, comment):
        params = {'text': comment}
        return self.makeRequest('POST', '/cards/' + card['id'] + '/actions/comments', params=params)

    def moveCard(self, card, list_id):
        params = {'idList': list_id}
        self.makeRequest('PUT', '/cards/' + card['id'], params=params)

    def makeRequest(self, method, path, params=None):
        if not params:
            params = {}
        params['key'] = self.api_key
        params['token'] = self.oauth_token
        
        url = self.base_url + path
        data = None

        if method == 'GET':
            url += '?' + urlencode(params)
        elif method in ['POST', 'PUT']:
            data = urlencode(params)

        request = Request(url)
        if method == 'PUT':
            request.get_method = lambda: method

        try:
            if data:
                response = urlopen(request, data=data)
            else:
                response = urlopen(request)
        except HTTPError:
            result = None
        else:
            result = json.loads(response.read())

        return result


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print 'Wrong number of arguments. Need api_key, oauth_token, board_id and list_name.'
        sys.exit()
    filename, api_key, oauth_token, board_id, list_name = sys.argv
    client = Trello(api_key, oauth_token, board_id)
    tlist = client.findList(list_name)
    if tlist:
        print 'List ID: ' + tlist['id']
    else:
        print 'List not found.'
