from argparse import ArgumentParser
from collections import defaultdict
import numpy as np
from common import AddedWord
import cPickle

class Stats(object):
    __slots__ = ['count', 'words', 'word']

    def __getstate__(self):
        return self.count, self.words, self.word

    def __setstate__(self, state):
        count, words, word = state
        self.count = count
        self.words = words
        self.word = word

    def __init__(self, word):
        self.count = 1
        self.words = defaultdict(int)
        self.word = word

    def add(self, word):
        self.words[word] += 1


class CollabPredict(object):
    def __init__(self, words_file):
        self.word_dict = {}
        self.total_users = 0
        with open(words_file, 'r') as f:
            self.init_from_file(f)

    @staticmethod
    def load(filename):
        with open(filename, 'rb') as file:
            return cPickle.load(file)

    def save(self, filename):
        with open(filename, 'wb') as file:
            cPickle.dump(self, file, -1)

    def init_from_file(self, file):
        prev_user = None
        words = []
        for line in file:
            parsed = AddedWord.parse(line)
            if not parsed or not parsed.source.startswith('search_'):
                continue
            word = parsed.word
            if prev_user is None:
                words = [word]
                prev_user = parsed.user_id
                continue

            if parsed.user_id != prev_user:
                self.append_word_pairs(words)
                prev_user = parsed.user_id
                words = []
            words.append(word)

        if len(words) > 0:
            self.append_word_pairs(words)

    def append_to_word_dict(self, word1, word2):
        if word1 in self.word_dict:
            stat = self.word_dict[word1]
        else:
            stat = Stats(word1)
        stat.add(word2)

    def append_word_pairs(self, words):
        self.total_users += 1

        words = words[:100]

        for word in words:
            if word in self.word_dict:
                stat = self.word_dict[word]
                stat.count += 1
            else:
                stat = Stats(word)
                self.word_dict[word] = stat

        for i in xrange(len(words)):
            word1 = words[i]
            for k in xrange(i + 1, len(words)):
                assert k > i
                word2 = words[k]
                self.word_dict[word1].add(word2)
                self.word_dict[word2].add(word1)

    def predict(self, seed, max_hypos):
        scores = defaultdict(float)
        for word in seed:
            if word not in self.word_dict:
                continue
            stat = self.word_dict[word]
            for hypo in stat.words:
                hypo_stat = self.word_dict[hypo]
                if hypo_stat.count < 10:
                    continue
                y = hypo_stat.count * 1.0 / self.total_users
                cond_y = stat.words[hypo] * 1.0 / stat.count
                score = np.log(cond_y/y) * np.log(hypo_stat.count)
                scores[hypo] += score

        max_hypos = int(max_hypos)
        return sorted(scores.items(), key=lambda (word, score): score, reverse=True)[:max_hypos]


def main(args):
    predict = CollabPredict(args.train)
    predict.save(args.model)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-t', '--train', default='user_words_train.tsv')
    parser.add_argument('-m', '--model', default='collab.model')
    args = parser.parse_args()

    main(args)
