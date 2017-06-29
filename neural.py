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
import os
from base64 import b64encode, b64decode
import random

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
                if (i + 1) % 1000000 == 0:
                    log.info('%sM lines done.' % ((i + 1)/1000000))
                    # break
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
        indexes = indexes[-self.seq_len:]
        seeds_vec = np.zeros(self.seq_len, dtype=np.uint32)
        seeds_vec[0:len(indexes)] = indexes
        return seeds_vec.reshape(self.seq_len)

    def batch_generator(self, batch_size):
        log.info('Building dataset...')
        self.added_words.sort(key=lambda x: (x.user_id, x.creation_time))
        epoch = 0
        users = [x[1] for x in it.groupby(self.added_words, key=lambda x: x.user_id)]
        X, Y = [], []
        while True:
            random.shuffle(users)
            for added_words in users:
                words = list(added_words)
                if len(words) < 6:
                    continue
                for i in xrange(5, len(words)):
                    seeds = [x.meaning.en for x in words[max(0, i - self.seq_len):i]]
                    x_vec = self.make_input_vector(seeds)
                    X.append(x_vec)

                    y_index = bisect_left(self.meanings, words[i].meaning)
                    assert self.meanings[y_index] == words[i].meaning
                    target = to_categorical(y_index, num_classes=len(self.meanings))
                    Y.append(target)
                    if len(X) >= batch_size:
                        yield epoch, np.array(X).reshape((len(X), self.seq_len)), np.array(Y).reshape((len(X), len(self.meanings)))
                        X = []
                        Y = []
            epoch += 1

    def train(self, train_file, args):
        self.read_vocabs(train_file)
        self.model = self.build_model()

        for epoch, X, Y in self.batch_generator(args.gen_batch_size):
            if epoch >= args.epochs:
                break
            self.model.fit(
                X, Y,
                batch_size=args.batch_size,
                epochs=1,
                validation_split=0.2,
                initial_epoch=epoch
            )


    def save(self, model_filename):
        self.model.save(model_filename, overwrite=True)
        with open(model_filename, 'rb') as weights_file:
            model_dump = weights_file.read()
        jdata = {
            'seq_len': self.seq_len,
            'min_freq': self.min_freq,
            'model': b64encode(model_dump),
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
            f.write(json.dumps(jdata, ensure_ascii=False, indent=4))

    @staticmethod
    def load(filename):
        with open(filename, 'r') as f:
            jdata = json.loads(f.read())
        self = NeuralPredict(jdata['min_freq'], jdata['seq_len'])
        self.vocab = [x.encode('utf-8') for x in jdata['vocab']]
        self.meanings = [Meaning(x['id'], x['en'].encode('utf-8'), x['ru'].encode('utf-8')) for x in jdata['meanings']]
        model_dump = b64decode(jdata['model'])
        with tempfile.NamedTemporaryFile('wb') as f:
            f.write(model_dump)
            f.flush()
            self.model = load_model(f.name)
        return self

    def predict(self, seeds, max_hypos):
        seed_vec = self.make_input_vector(seeds)
        X = np.array(seed_vec).reshape((1, self.seq_len))
        output = self.model.predict(X)[0]
        expect_count = len(seeds) + max_hypos

        seeds = set(seeds)

        indexes = np.argpartition(output, -expect_count)[-expect_count:]
        result_items = list([{'word': self.meanings[i], 'score': output[i]} for i in indexes])
        result_items.sort(key=lambda x: x['score'], reverse=True)  # sort by score
        res = []
        for item in result_items:
            meaning = item['word']
            score = item['score']
            if meaning.en in seeds:
                continue
            res.append({'word': meaning, 'score': float(score)})
            if len(res) >= max_hypos:
                break
        return res


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
    parser.add_argument('-g', '--gen-batch-size', default=100000, type=int, help='Batch size for dataset generator')
    parser.add_argument('-t', '--train', default='user_words_train.tsv')
    parser.add_argument('-m', '--model', default='neural.model')
    args = parser.parse_args()

    main(args)
