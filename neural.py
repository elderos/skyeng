from argparse import ArgumentParser
from collections import defaultdict
import itertools as it
import os

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from common import AddedWord, log, Meaning
from keras.models import Sequential, load_model
from keras.layers import Embedding, Dense, GRU, Dropout
from bisect import bisect_left
import numpy as np
import ujson as json
import tempfile
from base64 import b64encode, b64decode
import random
import signal
import tensorflow as tf

random.seed = 100500

sigint_pressed = False


def on_sigint(signal, frame):
    global sigint_pressed
    sigint_pressed = True
    log.info('Catched SIGINT. Use SIGQUIT to exit immediately (Ctrl+\\)')


class NeuralPredict(object):
    def __init__(self, min_freq, seq_len):
        self.vocab = []
        self.meanings = []
        self.added_words = []
        self.min_freq = min_freq
        self.seq_len = seq_len
        self.graph = tf.get_default_graph()
        self.model = None

    def build_model(self):
        model = Sequential([
            Embedding(
                input_dim=len(self.vocab) + 1,
                output_dim=100,
                input_length=self.seq_len,
                mask_zero=True,
                # embeddings_regularizer='l2'
            ),
            Dropout(0.2),
            GRU(100, 
                activation='tanh',
                # activity_regularizer='l2'
                ),
            Dropout(0.2),
            Dense(250, activation='tanh'),
            Dropout(0.2),
            Dense(len(self.meanings), activation='softmax')
        ])

        model.summary()
        model.compile(optimizer='nadam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
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
                # if not added_word.source.startswith('search_'):
                #     continue
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

    def fill_input_vectors(self, seeds_arr, batch_arr, offset):
        for i, seeds in enumerate(seeds_arr):
            batch_arr[offset + i] *= 0
            seed_num = min([self.seq_len, len(seeds)])
            for k in xrange(seed_num):
                seed = seeds[-seed_num + k]
                batch_arr[offset + i][k] = self.vocab_index(seed)

    def batch_generator(self, batch_size):
        log.info('Start building dataset')
        log.info('Sorting added words')
        self.added_words.sort(key=lambda x: (x.user_id, x.creation_time))
        epoch = 0
        log.info('Grouping by user')
        users = [list(x[1]) for x in it.groupby(self.added_words, key=lambda x: x.user_id)]
        log.info('Allocating buffers')
        X = np.ndarray(shape=(batch_size, self.seq_len), dtype=np.int32)
        Y = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
        X_pos = 0
        log.info('Start filling buffers')
        random.shuffle(users)
        while True:
            for added_words in users:
                words = added_words
                if len(words) < 6:
                    continue
                for i in xrange(5, len(words)):
                    seeds = [x.meaning.en for x in words[max(0, i - self.seq_len):i]]
                    self.fill_input_vectors([seeds], X, X_pos)
                    y_index = bisect_left(self.meanings, words[i].meaning)
                    assert self.meanings[y_index] == words[i].meaning
                    Y[X_pos] *= 0
                    Y[X_pos][0] = y_index
                    X_pos += 1

                    if X_pos >= len(X):
                        yield epoch, X, Y
                        X_pos = 0
            if X_pos > 0:
                yield epoch, X[0:X_pos], Y[0:X_pos]
                X_pos = 0

            epoch += 1

    def train(self, train_file, args):
        self.read_vocabs(train_file)
        if not self.model:
            self.model = self.build_model()

        signal.signal(signal.SIGINT, on_sigint)
        batch_no = 0
        epoch_train_losses = []
        epoch_val_losses = []
        epoch_acc = []
        epoch_val_acc = []
        prev_epoch = None
        for epoch, X, Y in self.batch_generator(args.gen_batch_size):
            if prev_epoch is not None and prev_epoch != epoch:
                avg_train = np.average(epoch_train_losses)
                avg_val = np.average(epoch_val_losses)
                avg_train_acc = np.average(epoch_acc)
                avg_val_acc = np.average(epoch_val_acc)
                log.info('Average epoch losses:')
                log.info('Train:\t%.6f' % avg_train)
                log.info('Val:\t%.6f' % avg_val)
                log.info('Train acc:\t%.6f' % avg_train_acc)
                log.info('Val acc:\t%.6f' % avg_val_acc)
                epoch_train_losses = []
                epoch_val_losses = []
                epoch_acc = []
                epoch_val_acc = []
                batch_no = 0

            prev_epoch = epoch

            if sigint_pressed:
                log.info('Stop training due to SIGINT catched.')
                break
            if epoch >= args.epochs:
                break
            history = self.model.fit(
                X, Y,
                batch_size=args.batch_size,
                epochs=1,
                validation_split=0.2,
                shuffle=False,
                verbose=0
                # initial_epoch=epoch,
            )
            if 'loss' in history.history and 'val_loss' in history.history:                
                log.info('Epoch #%s, batch #%s: training loss %.6f | acc %.6f || val loss %.6f | acc %.6f' % (
                    epoch,
                    batch_no,
                    history.history['loss'][-1],
                    history.history['acc'][-1],
                    history.history['val_loss'][-1],
                    history.history['val_acc'][-1]
                ))
                epoch_train_losses.append(history.history['loss'][-1])
                epoch_val_losses.append(history.history['val_loss'][-1])
                epoch_acc.append(history.history['acc'][-1])
                epoch_val_acc.append(history.history['val_acc'][-1])
            else:
                log.info(str(history.history.keys()))
            batch_no += 1


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
        seed_vec = np.ndarray(shape=(1, self.seq_len))
        seeds = list(set([x for x in seeds]))
        self.fill_input_vectors([seeds], seed_vec, 0)
        with self.graph.as_default():
            output = self.model.predict(seed_vec)[0]
        expect_count = len(seeds) + max_hypos

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
    if args.preload:
        model = NeuralPredict.load(args.preload)
    else:
        model = NeuralPredict(3, 30)

    model.train(args.train, args)
    log.info('Saving model to %s...' % args.model)
    model.save(args.model)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-e', '--epochs', default=10, type=int)
    parser.add_argument('-b', '--batch-size', default=1000, type=int)
    parser.add_argument('-g', '--gen-batch-size', default=10000, type=int, help='Batch size for dataset generator')
    parser.add_argument('-t', '--train', default='user_words_train.json')

    parser.add_argument('-m', '--model', default='neural.model')
    parser.add_argument('-p', '--preload', help='Preload trained model')
    args = parser.parse_args()

    main(args)
