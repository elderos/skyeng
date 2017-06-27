#!/usr/bin/env python

from argparse import ArgumentParser
import cherrypy
from cherrypy.lib.static import serve_file
import os
import ujson as json
from collab import CollabPredict

class WordPredict(object):
    def __init__(self):
        self.methods = {
            'collab': CollabPredict.load('collab.model'),
        }

    @cherrypy.expose
    def index(self):
        return serve_file('static/index.html')

    @cherrypy.expose
    @cherrypy.tools.json_out
    def get_predicted_words(self, seeds):
        jdata = json.loads(seeds)



def main(args):
    cherrypy.quickstart(WordPredict(), '/skyeng', config={
        'server.socket_port': args.port,
        'tools.staticdir.on': True,
        'tools.staticdir.dir': '/home/site/skyeng/static',
        'tools.staticdir.index': 'index.html'
    })
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=50000)
    
    args = parser.parse_args()
    main(args)
