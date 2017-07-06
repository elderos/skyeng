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
from common import AddedWord
import random
import itertools as it


class WordPredict(object):
    def __init__(self, validate_filepath):
        cherrypy.log('Initializing methods...')

        self.methods = [{
            'name': 'neural', 'method': NeuralPredict.load('neural_w_lessons2.model'),
        }, {
            'name': 'collab', 'method': CollabPredict.load('collab.model'),
        }, {
            'name': 'glovec', 'method': GlovePredict('glove.6B.50d.txt'),
        }]
        self.random_users = []
        self.random_lessons = []
        with open(validate_filepath, 'r') as f:
            words = []
            for line in f:
                word = AddedWord.parse(line)
                if word:
                    words.append(word)
            words.sort(key=lambda x: (x.user_id, x.source))
            for user, words in it.groupby(words, key=lambda x: x.user_id):
                en_words = list(set([w.meaning.en for w in words]))
                if len(en_words) < 3:
                    continue
                self.random_users.append(en_words)

            for (user, source), words in it.groupby(words, key=lambda x: (x.user_id, x.source)):
                if not source.startswith('lesson_'):
                    continue
                en_words = list(set([w.meaning.en for w in words]))
                if len(words) < 3:
                    continue
                self.random_lessons.append(en_words)

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

    @cherrypy.expose
    def random_user(self):
        words = random.choice(self.random_users)
        return json.dumps(words)

    @cherrypy.expose
    def random_lesson(self):
        words = random.choice(self.random_lessons)
        return json.dumps(words)

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
        WordPredict(args.validate),
        '/skyeng'
    )
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=50000)
    parser.add_argument('-v', '--validate', default='user_words_validate.json')
    
    args = parser.parse_args()
    main(args)
