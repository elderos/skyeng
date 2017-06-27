from argparse import ArgumentParser
import sys
from common import AddedWord


def main(args):
    lines = [x.rstrip() for x in sys.stdin]
    items = [AddedWord.parse(x) for x in lines]
    items = [x for x in items if x and x.validate()]
    items.sort(key=lambda x: (x.user_id, x.creation_time))

    for item in items:
        print item

    
if __name__ == '__main__':
    parser = ArgumentParser()

    
    args = parser.parse_args()
    main(args)
