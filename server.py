#!/usr/bin/env python

from argparse import ArgumentParser
import cherrypy
from cherrypy.lib.static import serve_file
import os
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # see issue #152
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import ujson as json
from collab import CollabPredict, Stats
import cherrypy_cors
from neural import NeuralPredict
from glovec import GlovePredict

class WordPredict(object):
    def __init__(self):
        cherrypy.log('Initializing methods...')
        self.methods =[{ 
            'name': 'neural', 'method': NeuralPredict.load('neural_w_lessons2.model'),
	}, {
            'name': 'collab', 'method': CollabPredict.load('collab.model'),
	}, {
            'name': 'glovec', 'method': GlovePredict('glove.6B.50d.txt'),
        }]

    @cherrypy.expose
    def index(self):
        return serve_file('static/index.html')

    @cherrypy.expose
    def get_predicted_words(self, seeds):
        jdata = [x.encode('utf-8') for x in json.loads(seeds)]
        res = []
        for obj in self.methods:
	    method_name = obj['name']
	    method = obj['method']
            res.append({
                'title': method_name,
                'words': [
                    {
                        'meaning_id': x['word'].meaning_id,
                        'en': x['word'].en,
                        'ru': x['word'].ru,
                        'score': x['score']
                    } for x in method.predict(jdata, 15)
                    ]
            })
        return json.dumps(res)


def CORS():
    cherrypy.response.headers['Access-Control-Allow-Origin'] = 'http://eantonov.name'
    # cherrypy.response.headers['Access-Control-Allow-Headers'] = '*'
    cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST'


def main(args):
    cherrypy_cors.install()
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)

    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': args.port,
        'log.access_file': './access.log',
        'log.error_file': './error.log',
        'tools.staticdir.on': True,
        'tools.staticdir.dir': os.getcwd() + '/static',
        'tools.staticdir.index': 'index.html',
        'tools.CORS.on': True,
        'cors.expose.on': True
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
