from argparse import ArgumentParser
import ujson as json
import sys
from common import DATE_FORMAT

def main(args):
    for line in sys.stdin:
        columns = line.rstrip().split('\t')
        if len(columns) != 6:
            continue
        jdata = {
            'user_id': int(columns[0]),
            'meaning_id': int(columns[1]),
            'creation_time': columns[2],
            'source': columns[3],
            'en': columns[4],
            'ru': columns[5]
        }
        print json.dumps(jdata, ensure_ascii=False)
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    #TODO: args
    
    args = parser.parse_args()
    main(args)
