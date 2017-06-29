from argparse import ArgumentParser
from collections import defaultdict
import itertools as it
from common import AddedWord, log, Meaning
from keras.models import Sequential, load_model
from keras.layers import Embedding, Dense, GRU
from bisect import bisect_left
import numpy as np
from keras.utils import to_categorical
import ujson as json
import tempfile
import gc
import os

class NeuralPredict(object):
    def __init__(self, min_freq, seq_len):
        self.vocab = []
        self.meanings = []
        self.added_words = []
        self.min_freq = min_freq
        self.seq_len = seq_len
        self.model = None

    def build_model(self):
        model = Sequential([
            Embedding(
                input_dim=len(self.vocab) + 1,
                output_dim=100,
                input_length=self.seq_len,
                mask_zero=True,
            ),
            GRU(40, return_sequences=False),
            Dense(len(self.meanings), activation='softmax')
        ])

        model.summary()
        model.compile(optimizer='rmsprop', loss='categorical_crossentropy')
        return model

    def read_vocabs(self, train_file):
        log.info('Reading vocabs...')
        words = defaultdict(int)
        meanings = set()
        with open(train_file, 'r') as f:
            for i, line in enumerate(f):
                if (i + 1) % 100000 == 0:
                    log.info('%s lines done.' % (i + 1))
                    break
                added_word = AddedWord.parse(line)
                if not added_word.source.startswith('search_'):
                    continue
                self.added_words.append(added_word)
                words[added_word.meaning.en] += 1
                meanings.add(added_word.meaning)

        self.meanings = list(meanings)
        self.meanings.sort()

        self.vocab = list([x for x in words if words[x] >= self.min_freq])
        self.vocab.sort()
        log.info('Total %s words and %s meanings' % (len(self.vocab), len(self.meanings)))

    def vocab_index(self, word):
        index = bisect_left(self.vocab, word)
        if index < len(self.vocab) and self.vocab[index] == word:
            return index + 1
        return 0

    def make_input_vector(self, seeds):
        indexes = [self.vocab_index(x) for x in seeds]
        indexes = [x for x in indexes if x > 0]
        indexes = indexes[:30]
        seeds_vec = np.zeros(self.seq_len, dtype=np.uint32)
        seeds_vec[0:len(indexes)] = indexes
        return seeds_vec

    def make_dataset(self):
        X, Y = [], []

        log.info('Building dataset...')
        self.added_words.sort(key=lambda x: (x.user_id, x.creation_time))
        i = 0
        for user_id, added_words in it.groupby(self.added_words, key=lambda x: x.user_id):
            i += 1
            if i % 20000 == 0:
                log.info('Total %s users done' % i)
            words = list(added_words)
            if len(words) < 6:
                continue
            for i in xrange(5, len(words)):
                seeds = [x.meaning.en for x in words[max(0, i - self.seq_len):i]]
                x_vec = self.make_input_vector(seeds)
                X.append(x_vec)

                y_index = bisect_left(self.meanings, words[i].meaning)
                assert self.meanings[y_index] == words[i].meaning
                target = to_categorical(y_index, num_classes=len(self.meanings)).reshape(len(self.meanings))
                Y.append(target)
        log.info('Total %s examples' % len(X))
        return np.array(X), np.array(Y)

    def train(self, train_file, args):
        self.read_vocabs(train_file)
        self.model = self.build_model()

        X, Y = self.make_dataset()

        self.added_words = None
        gc.collect()

        self.model.fit(
            X, Y,
            batch_size=args.batch_size,
            epochs=args.epochs,
            validation_split=0.2
        )

    def save(self, model_filename):
        self.model.save(model_filename, overwrite=True)
        with open(model_filename, 'rb') as weights_file:
            model_dump = weights_file.read()
        jdata = {
            'seq_len': self.seq_len,
            'min_freq': self.min_freq,
            'model': model_dump,
            'vocab': self.vocab,
            'meanings': [{
                    'id': x.meaning_id,
                    'en': x.en,
                    'ru': x.ru
                } for x in self.meanings
            ]
        }
        os.remove(model_filename)
        with open(model_filename, 'w') as f:
            json.dump(jdata, f)

    @staticmethod
    def load(filename):
        with open(filename, 'r') as f:
            jdata = json.load(f)
        self = NeuralPredict(jdata['min_freq'], jdata['seq_len'])
        self.vocab = jdata['vocab']
        self.meanings = [Meaning(x['id'], x['en'], x['ru']) for x in jdata['meanings']]
        model_dump = jdata['model']
        with tempfile.NamedTemporaryFile('wb') as f:
            f.write(model_dump)
            self.model = load_model(f.name)
        return self


def main(args):
    log.info('Training predict (input: %s)' % args.train)
    model = NeuralPredict(3, 30)
    model.train(args.train, args)
    log.info('Saving model to %s...' % args.model)
    model.save(args.model)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-e', '--epochs', default=10, type=int)
    parser.add_argument('-b', '--batch-size', default=2048, type=int)
    parser.add_argument('-t', '--train', default='user_words_train.tsv')
    parser.add_argument('-m', '--model', default='neural.model')
    args = parser.parse_args()

    main(args)
