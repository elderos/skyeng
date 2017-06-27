from argparse import ArgumentParser
import sys
from common import AddedWord
import itertools as it
from collections import defaultdict
import numpy as np
import logging


def init_logging():
    formatter = logging.Formatter('%(asctime)s %(message)s')

    log = logging.getLogger('skyeng')
    log.setLevel(logging.INFO)
    log.propagate = False

    fh = logging.FileHandler('skyeng_log.txt')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    log.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    log.addHandler(ch)

    return log


log = init_logging()


class Stats(object):
    __slots__ = ['count', 'words', 'word']

    def __init__(self, word):
        self.count = 1
        self.words = defaultdict(int)
        self.word = word

    def add(self, word):
        self.words[word] += 1


word_dict = {}
total_users = 0


def append_to_word_dict(word1, word2):
    global word_dict

    if word1 in word_dict:
        stat = word_dict[word1]
    else:
        stat = Stats(word1)
    stat.add(word2)


def append_word_pairs(words):
    global total_users
    total_users += 1

    words = words[:100]

    for word in words:
        if word in word_dict:
            stat = word_dict[word]
            stat.count += 1
        else:
            stat = Stats(word)
            word_dict[word] = stat

    for i in xrange(len(words)):
        word1 = words[i]
        for k in xrange(i + 1, len(words)):
            assert k > i
            word2 = words[k]
            word_dict[word1].add(word2)
            word_dict[word2].add(word1)


def predict(seed):
    global total_users
    scores = defaultdict(float)
    for word in seed:
        if word not in word_dict:
            continue
        stat = word_dict[word]
        for hypo in stat.words:
            hypo_stat = word_dict[hypo]
            if hypo_stat.count < 10:
                continue
            y = hypo_stat.count * 1.0 / total_users
            cond_y = stat.words[hypo] * 1.0 / stat.count
            score = np.log(cond_y/y) * np.log(hypo_stat.count)
            scores[hypo] += score

    max_hypos = 30
    return sorted(scores.items(), key=lambda (word, score): score, reverse=True)[:max_hypos]


def main(args):
    validate_users = []
    prev_user = None
    words = []
    i = 0
    for line in sys.stdin:
        parsed = AddedWord.parse(line)
        if not parsed:
            continue
        word = parsed.word
        if prev_user is None:
            i += 1
            words = [word]
            prev_user = parsed.user_id
            continue

        if parsed.user_id != prev_user:
            i += 1
            if i % 10 == 0:
                validate_users.append(words)
            else:
                append_word_pairs(words)
            prev_user = parsed.user_id
            words = []
        words.append(word)

    if len(words) > 0:
        append_word_pairs(words)

    for words in validate_users:
        word_count = len(words)
        if word_count < 20:
            continue
        boundary = len(words) / 2
        seed = set(words[:boundary])
        actual = set(words[boundary:])
        predicted = predict(seed)

        print '-' * 30
        print '-' * 30
        print 'Seed:'
        for word in seed:
            print word
        print '-' * 30
        print 'Actual:'
        actual = sorted(actual, key=lambda x: x.en)
        for word in actual:
            print word

        predicted = sorted(predicted, key=lambda x: x[1])
        print '-' * 30
        print 'Predicted:'
        intersected = 0
        for word, score in predicted:
            if word in actual:
                intersected += 1
            if word in seed:
                continue
            print word, score
        print 'Intersection: %s of %s/%s' % (intersected, len(actual), len(predicted))

    
if __name__ == '__main__':
    parser = ArgumentParser()
    # parser.add_argument('input')
    
    args = parser.parse_args()
    main(args)
