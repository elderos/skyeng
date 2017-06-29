from argparse import ArgumentParser
from collab import CollabPredict, Stats
from common import AddedWord, log
from neural import NeuralPredict


def main(args):
    log.info('Initializing model...')
    alg = NeuralPredict.load(args.model)
    #CollabPredict.load(args.model)

    log.info('Reading validate pool...')
    validate_users = []
    prev_user = None
    with open(args.validate, 'r') as f:
        meanings = []
        for line in f:
            parsed = AddedWord.parse(line)
            if not parsed or not parsed.source.startswith('search_'):
                continue
            meaning = parsed.meaning
            if prev_user is None:
                meanings = [meaning]
                prev_user = parsed.user_id
                continue

            if parsed.user_id != prev_user:
                validate_users.append(meanings)
                prev_user = parsed.user_id
                meanings = []
            meanings.append(meaning)
        if len(meanings) > 0:
            validate_users.append(meanings)

    log.info('Validating...')
    for meanings in validate_users:
        word_count = len(meanings)
        if word_count < 20:
            continue
        boundary = len(meanings) / 2
        seed = set([x.en for x in meanings[:boundary]])
        actual = set(meanings[boundary:])
        predicted = alg.predict(seed, args.hypos_count + len(seed))

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

        predicted = sorted(predicted, key=lambda x: x['score'], reverse=True)
        print '-' * 30
        print 'Predicted:'
        intersected = 0
        predicted_len = 0
        for item in predicted:
            meaning = item['word']
            score = item['score']
            if meaning in actual:
                intersected += 1
            if meaning.en in seed:
                continue
            predicted_len += 1
            print meaning, '%.4f' % score, meaning in actual
            if predicted_len >= args.hypos_count:
                break
        print 'Intersection: %s of %s/%s' % (intersected, len(actual), predicted_len)

    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-m', '--model', required=True)
    parser.add_argument(
        '-v',
        '--validate',
        default='user_words_validate.tsv',
        metavar='FILE',
        help='Validate file (default: user_words_validate.tsv)'
    )
    parser.add_argument('-c', '--hypos-count', type=int, default=30)
    
    args = parser.parse_args()
    main(args)
