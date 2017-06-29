from argparse import ArgumentParser
from collections import defaultdict
import numpy as np
from common import AddedWord, log
import cPickle


class Stats(object):
    __slots__ = ['count', 'meanings', 'word']

    def __getstate__(self):
        return self.count, self.meanings, self.word

    def __setstate__(self, state):
        count, meanings, word = state
        self.count = count
        self.meanings = meanings
        self.word = word

    def __init__(self, word):
        self.count = 1
        self.meanings = defaultdict(int)
        self.word = word

    def add(self, meaning):
        self.meanings[meaning] += 1


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
            meanings_to_delete = []
            if stat.count < self.min_self_count:
                keys_to_delete.append(key)
                continue

            for meaning, count in stat.meanings.iteritems():
                if count < self.min_hypo_count:
                    meanings_to_delete.append(meaning)
            for meaning in meanings_to_delete:
                del stat.meanings[meaning]
            if len(stat.meanings) < 1:
                keys_to_delete.append(key)
                continue

        for key in keys_to_delete:
            del self.word_dict[key]

        for key, stat in self.word_dict.iteritems():
            meanings_to_delete = []
            for meaning in stat.meanings:
                if meaning.en not in self.word_dict:
                    meanings_to_delete.append(meaning)
            for meaning in meanings_to_delete:
                del stat.words[meaning]

    @staticmethod
    def load(filename):
        with open(filename, 'rb') as file:
            return cPickle.load(file)

    def save(self, filename):
        with open(filename, 'wb') as file:
            cPickle.dump(self, file, -1)

    def init_from_file(self, file):
        prev_user = None
        meanings = []

        for i, line in enumerate(file):
            if (i + 1) % 100000 == 0:
                log.info('Total %s lines done.' % (i + 1))
            parsed = AddedWord.parse(line)
            if not parsed or not parsed.source.startswith('search_'):
                continue
            meaning = parsed.meaning
            if prev_user is None:
                meanings = [meaning]
                prev_user = parsed.user_id
                continue

            if parsed.user_id != prev_user:
                self.append_word_pairs(meanings)
                prev_user = parsed.user_id
                meanings = []
            meanings.append(meaning)

        if len(meanings) > 0:
            self.append_word_pairs(meanings)

    def append_word_pairs(self, meanings):
        self.total_users += 1

        meanings = meanings[:100]

        for meaning in meanings:
            if meaning.en in self.word_dict:
                stat = self.word_dict[meaning.en]
                stat.count += 1
            else:
                stat = Stats(meaning.en)
                self.word_dict[meaning.en] = stat

        for i in xrange(len(meanings)):
            meaning1 = meanings[i]
            for k in xrange(i + 1, len(meanings)):
                assert k > i
                meaning2 = meanings[k]
                self.word_dict[meaning1.en].add(meaning2)
                self.word_dict[meaning2.en].add(meaning1)

    def predict(self, seed, max_hypos):
        scores = defaultdict(float)
        for word in seed:
            if word not in self.word_dict:
                continue
            stat = self.word_dict[word]
            for hypo in stat.meanings:
                hypo_stat = self.word_dict[hypo.en]
                if hypo_stat.count < 10 or stat.meanings[hypo] < 5:
                    continue
                y = hypo_stat.count * 1.0 / self.total_users
                cond_y = stat.meanings[hypo] * 1.0 / stat.count
                score = np.log(cond_y/y) * np.log(hypo_stat.count)
                scores[hypo] += score

        max_hypos = int(max_hypos)
        res = []
        for meaning, score in sorted(scores.items(), key=lambda (w, s): s, reverse=True):
            if meaning.en in seed:
                continue
            if len(res) >= max_hypos:
                break
            res.append({'word': meaning, 'score': score})
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
