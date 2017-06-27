from argparse import ArgumentParser
from collab import CollabPredict, Stats
from common import AddedWord, log


def main(args):
    log.info('Initializing model...')
    alg = CollabPredict.load(args.model)

    log.info('Reading validate pool...')
    validate_users = []
    prev_user = None
    with open(args.validate, 'r') as f:
        words = []
        for line in f:
            parsed = AddedWord.parse(line)
            if not parsed or not parsed.source.startswith('search_'):
                continue
            word = parsed.word
            if prev_user is None:
                words = [word]
                prev_user = parsed.user_id
                continue

            if parsed.user_id != prev_user:
                validate_users.append(words)
                prev_user = parsed.user_id
                words = []
            words.append(word)
        if len(words) > 0:
            validate_users.append(words)

    log.info('Validating...')
    for words in validate_users:
        word_count = len(words)
        if word_count < 20:
            continue
        boundary = len(words) / 2
        seed = set(words[:boundary])
        actual = set(words[boundary:])
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

        predicted = sorted(predicted, key=lambda x: x[1], reverse=True)
        print '-' * 30
        print 'Predicted:'
        intersected = 0
        predicted_len = 0
        for word, score in predicted:
            if word in actual:
                intersected += 1
            if word in seed:
                continue
            predicted_len += 1
            print word, score
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
