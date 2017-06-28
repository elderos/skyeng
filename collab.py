from argparse import ArgumentParser
from collections import defaultdict
import numpy as np
from common import AddedWord, log
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
    def __init__(self, words_file, min_self_count=5, min_hypo_count=3):
        self.word_dict = {}
        self.total_users = 0
        self.min_self_count = min_self_count
        self.min_hypo_count = min_hypo_count
        log.info('Reading input file...')
        with open(words_file, 'r') as f:
            self.init_from_file(f)

        log.info('Pruning model...')
        self.prune()

    def prune(self):
        keys_to_delete = []

        for key, stat in self.word_dict.iteritems():
            words_to_delete = []
            if stat.count < self.min_self_count:
                keys_to_delete.append(key)
                continue

            for word, count in stat.words.iteritems():
                if count < self.min_hypo_count:
                    words_to_delete.append(word)
            for word in words_to_delete:
                del stat.words[word]
            if len(stat.words) < 1:
                keys_to_delete.append(key)
                continue

        for key in keys_to_delete:
            del self.word_dict[key]

        for key, stat in self.word_dict.iteritems():
            words_to_delete = []
            for word in stat.words:
                if word.en not in self.word_dict:
                    words_to_delete.append(word)
            for word in words_to_delete:
                del stat.words[word]

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

        for i, line in enumerate(file):
            if (i + 1) % 100000 == 0:
                log.info('Total %s lines done.' % (i + 1))
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
            stat = self.word_dict[word1.en]
        else:
            stat = Stats(word1)
        stat.add(word2)

    def append_word_pairs(self, words):
        self.total_users += 1

        words = words[:100]

        for word in words:
            if word.en in self.word_dict:
                stat = self.word_dict[word.en]
                stat.count += 1
            else:
                stat = Stats(word)
                self.word_dict[word.en] = stat

        for i in xrange(len(words)):
            word1 = words[i]
            for k in xrange(i + 1, len(words)):
                assert k > i
                word2 = words[k]
                self.word_dict[word1.en].add(word2)
                self.word_dict[word2.en].add(word1)

    def predict(self, seed, max_hypos):
        scores = defaultdict(float)
        for word in seed:
            if word not in self.word_dict:
                continue
            stat = self.word_dict[word]
            for hypo in stat.words:
                hypo_stat = self.word_dict[hypo.en]
                if hypo_stat.count < 10 or stat.words[hypo] < 5:
                    continue
                y = hypo_stat.count * 1.0 / self.total_users
                cond_y = stat.words[hypo] * 1.0 / stat.count
                score = np.log(cond_y/y) * np.log(hypo_stat.count)
                scores[hypo] += score

        max_hypos = int(max_hypos)
        res = []
        for word, score in sorted(scores.items(), key=lambda (w, s): s, reverse=True):
            if word.en in seed:
                continue
            if len(res) >= max_hypos:
                break
            res.append({'word': word, 'score': score})
        return res


def main(args):
    log.info('Training predict (input: %s)' % args.train)
    predict = CollabPredict(args.train)
    log.info('Saving model to %s...' % args.model)
    predict.save(args.model)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-t', '--train', default='user_words_train.tsv')
    parser.add_argument('-m', '--model', default='collab.model')
    args = parser.parse_args()

    main(args)
