from argparse import ArgumentParser
import cherrypy
from cherrypy.lib.static import serve_file


class WordPredict(object):

    @cherrypy.expose
    def index(self):
        return serve_file('static/index.html')


def main(args):
    #TODO
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    #TODO: args
    
    args = parser.parse_args()
    main(args)
