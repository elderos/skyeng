#!/usr/bin/env python

from argparse import ArgumentParser
import cherrypy
from cherrypy.lib.static import serve_file
import os
import ujson as json
from collab import CollabPredict, Stats

class WordPredict(object):
    def __init__(self):
        cherrypy.log('Initializing methods...')
        self.methods = {
            #'collab': CollabPredict.load('collab.model'),
        }

    @cherrypy.expose
    def index(self):
        return serve_file('static/index.html')

    @cherrypy.expose
    def get_predicted_words(self, seeds):
        jdata = json.loads(seeds)
        res = []
        for method_name, method in self.methods.items():
            res.append({
                method_name: [method.predict(jdata)]
            })



def main(args):
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': args.port,
        'log.access_file': './access.log',
        'log.error_file': './error.log',
        'tools.staticdir.on': True,
        'tools.staticdir.dir': '/home/site/skyeng/static',
        'tools.staticdir.index': 'index.html'
    })
    cherrypy.quickstart(
        WordPredict(),
        '/skyeng'
    )
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=50000)
    
    args = parser.parse_args()
    main(args)
