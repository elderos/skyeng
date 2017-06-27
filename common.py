from datetime import datetime

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class Word(object):
    __slots__ = ['meaning_id', 'en', 'ru']

    def __init__(self, meaning_id, en, ru):
        self.meaning_id = meaning_id
        self.en = en
        self.ru = ru

    def __eq__(self, other):
        return self.meaning_id == other.meaning_id

    def __ne__(self, other):
        return self.meaning_id != other.meaning_id

    def __hash__(self):
        return hash(self.meaning_id)

    def __str__(self):
        return '\t'.join([
            str(self.meaning_id),
            self.en,
            self.ru
        ])

    def __repr__(self):
        return str(self)


class AddedWord(object):
    __slots__ = ['user_id', 'word', 'creation_time', 'source']

    def __init__(self, user_id, meaning_id, creation_time, source, en, ru):
        self.user_id = int(user_id)
        self.word = Word(int(meaning_id), en, ru)
        self.creation_time = datetime.strptime(creation_time, DATE_FORMAT)
        self.source = source

    @staticmethod
    def parse(line):
        columns = line.rstrip().split('\t')
        if len(columns) != 6:
            return None
        return AddedWord(*columns)

    def validate(self):
        return self.user_id

    def __str__(self):
        return '\t'.join([
            str(self.user_id),
            str(self.word.meaning_id),
            self.creation_time.strftime(DATE_FORMAT),
            self.source,
            self.word.en,
            self.word.ru
        ])

    def __repr__(self):
        return str(self)
