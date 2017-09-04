import requests
import argparse
import hashlib
import random
import time

class OnlineHashCrack():
    def __init__(self, user_agent='PythonOnlineHashCracker', timeout=3):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = user_agent
    def _fetch(self, hashed):
        raise None
    def get(self, hashed, retry=3):
        for i in range(3):
            result = self._fetch(hashed)
            if result is not None:
                if hashlib.md5(result.encode()).hexdigest() == hashed:
                    return result
        return None
    def submit(self, hashed, result):
        if hashlib.md5(result.encode()).hexdigest() == hashed:
            self._submit(hashed, result)
    def _submit(self, hashed, result):
        pass
class Nitrxgen(OnlineHashCrack):
    def __repr__(self):
        return 'Nitrxgen'
    def _fetch(self, hashed):
        try:
            r = self.session.get('https://www.nitrxgen.net/md5db/' + hashed,
                                 timeout=self.timeout)
            return r.text
        except Exception as error:
            print(error.with_traceback(None))
class CrackHash(OnlineHashCrack):
    def __repr__(self):
        return 'CrackHash'
    def _fetch(self, hashed):
        try:
            r = self.session.get('https://crackhash.com/api.php?hash=' + hashed,
                                 timeout=self.timeout)
            return r.text
        except Exception as error:
            print(error.with_traceback(None))
    def _submit(self, hashed, result):
        try:
            r = self.session.get(
                'https://crackhash.com/api.php?share=%s&text=%s'
                % (hashed, result), timeout=self.timeout)
            print('Submitted:', hashed, result)
        except Exception as error:
            print(error.with_traceback(None))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('-f', '--found', default='found.txt')
    parser.add_argument('-l', '--left', default='left.txt')
    parser.add_argument('-s', '--submit', action='store_true')
    parser.add_argument('-d', '--dictionary', help='Store list of passwords to '
                        'be used as a dictionary in a hash cracker.')
    parser.add_argument('-t', '--timeout', type=int, default='3')
    args = parser.parse_args()
    online_hash_crackers = [Nitrxgen(timeout=args.timeout),
                            CrackHash(timeout=args.timeout)]
    if args.submit:
        with open(args.target) as file:
            for i in file.read().splitlines():
                i = i.split(':')
                if len(i) == 2:
                    hashed, result = i
                    if hashlib.md5(result.encode()).hexdigest() == hashed:
                        print(i)
                        for cracker in online_hash_crackers:
                            cracker.submit(hashed, result)
    else:  
        with open(args.target) as file:
            hashes = set(file.read().splitlines())
        print('Starting')
        success = {}
        length = len(hashes)
        try:
            for i, hashed in enumerate(hashes):
                random.shuffle(online_hash_crackers)
                print('%s/%s' % (i, length), end=' ')
                for cracker in online_hash_crackers:
                    result = cracker.get(hashed)
                    if result is not None:
                        success[hashed] = result
                        print('Success:', cracker, hashed, result)
                        for cracker2 in online_hash_crackers:
                            if cracker != cracker2:
                                cracker2.submit(hashed, result)
                        break
                if hashed not in success:
                    print('Failed:', hashed)
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
        with open(args.found, 'w') as file:
            file.write('\n'.join(':'.join((i, success[i])) for i in success))
        with open(args.left, 'w') as file:
            file.write('\n'.join(i for i in hashes if i not in success))
        if args.dictionary:
            with open(args.dictionary, 'w') as file:
                file.write('\n'.join(success[i] for i in success))


if __name__ == '__main__':
    main()
