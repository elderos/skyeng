from argparse import ArgumentParser
import nmslib
import numpy as np
from common import log, Meaning
from collections import defaultdict
import re
import string


class GlovePredict(object):
    def __init__(self, filename):
        self.index = nmslib.init(method='hnsw', space='cosinesimil')
        self.words = []
        self.vec_dict = {}
        log.info('Reading glovec file')
        with open(filename, 'r') as f:
            for i, line in enumerate(f):
                word, points = line.rstrip().split(' ', 1)
                self.words.append(word)
                vec = np.fromstring(points, sep=' ')
                self.vec_dict[word] = vec
                self.index.addDataPoint(i, vec)
        self.index.createIndex({'post': 2}, print_progress=True)
        log.info('Total %s words' % len(self.words))

    def strip_siffixes(self, word):
        for suf in ['ing', 'ed', 's']:
            if not word.endswith(suf):
                continue
            return word[:-len(suf)]
        return word

    def is_bad_word(self, word):
        if any([word.endswith(suf) for suf in ['ing', 'ed']]):
            return True
        if any([ch in word for ch in '0123456789`']):
            return True
        if re.match('[%s]' % re.escape(string.punctuation), word, flags=re.U) is not None:
            return True
        if re.match(r'\d', word, flags=re.U):
            return True
        return False

    def predict(self, seeds, count=30):
        seeds = set([x for x in seeds])
        hypos = defaultdict(lambda: [])

        vectors = np.array([self.vec_dict[seed] for seed in seeds if seed in self.vec_dict])

        neighbours = self.index.knnQueryBatch(vectors, k=count + len(seeds), num_threads=4)

        for ids, distances in neighbours:
            for id, distance in zip(ids, distances):
                hypos[id].append(distance)

        reduced = []
        for id, distances in hypos.items():
            word = self.words[id]
            if word in seeds:
                continue
            if self.strip_siffixes(word) in seeds:
                continue
            if self.is_bad_word(word):
                continue

            reduced.append((word, min(distances)))

        reduced.sort(key=lambda x: x[1])

        res = [{
            'word': Meaning(0, word, ''),
            'score': float(score)
        } for word, score in reduced[:count]
        ]

        return res

def main(args):
    method = GlovePredict(args.glovec)
    res = method.predict(['owl', 'sparrow', 'crow'], 30)
    print res
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-g', '--glovec', metavar='FILE', default='glove.6B.50d.txt')
    
    args = parser.parse_args()
    main(args)
