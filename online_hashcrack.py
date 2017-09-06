import argparse
import hashlib
import random
import codecs
import re

import requests


class OnlineHashCrack():
    def __init__(self, timeout=3, retry=3,
                 user_agent='PythonOnlineHashCracker', proxy=None):
        self.retry = retry
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = user_agent
        if proxy:
            self.session.proxies = {'http':proxy, 'https':proxy}

    def _fetch(self, _):
        pass

    def get(self, hashed):
        self.session.cookies.clear_expired_cookies()
        for _ in range(self.retry):
            try:
                for result in self._fetch(hashed):
                    if hashlib.md5(result.encode()).hexdigest() == hashed:
                        return result
                return None
            except requests.exceptions.ReadTimeout as error:
                print(self, 'timed out.')
            except requests.exceptions.ConnectionError:
                print(self, 'failed to connect.')
            except Exception as error:
                print(type(error), error)

    def submit(self, hashed, result):
        self.session.cookies.clear_expired_cookies()
        if hashlib.md5(result.encode()).hexdigest() == hashed:
            self._submit(hashed, result)

    def _submit(self, hashed, result):
        pass


class Nitrxgen(OnlineHashCrack):
    def __repr__(self):
        return 'Nitrxgen'

    def _fetch(self, hashed):
        r = self.session.get('https://www.nitrxgen.net/md5db/' + hashed,
                             timeout=self.timeout)
        yield r.text


class CrackHash(OnlineHashCrack):
    def __repr__(self):
        return 'CrackHash'

    def _fetch(self, hashed):
        r = self.session.get('https://crackhash.com/api.php?hash=' + hashed,
                             timeout=self.timeout)
        yield r.text
        match = re.fullmatch(r'\$HEX\[([a-f0-9]+)\]', r.text)
        if match:
            yield codecs.decode(match.group(1), 'hex').decode('utf-8')

    def _submit(self, hashed, result):
        try:
            r = self.session.get(
                'https://crackhash.com/api.php?share=%s&text=%s'
                % (hashed, result), timeout=self.timeout)
            print('Submitted:', hashed, result)
        except Exception as error:
            print(type(error), error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', help='File containing md5 hashes.')
    parser.add_argument('-f', '--found', default='found.txt', help='File to '
                        'store found hashes, default is found.txt.')
    parser.add_argument('-l', '--left', default='left.txt', help='File to '
                        'store remaining hashes, default is left.txt.')
    parser.add_argument('-s', '--submit', action='store_true',
                        help='Enable submit mode, submits hash file to '
                        'databases. The file should be in hash:passwd format, '
                        'like in a hashcat potfile')
    parser.add_argument('-d', '--dictionary', default='dict.txt', help='File '
                        'to store list of passwords to be used as a dictionary '
                        'in a hash cracker.')
    parser.add_argument('-t', '--timeout', type=int, default='15',
                        help='HTTP timeout(in seconds) to be used for the API '
                        'requests, default is 15')
    parser.add_argument('-r', '--retry', type=int, default='3',
                        help='Number of retries to attempt for HTTP requests.')
    parser.add_argument('-p', '--proxy', help='Use specified prpxy.')
    args = parser.parse_args()
    online_hash_crackers = []
        now = cracker(timeout=args.timeout, retry=args.retry, proxy=args.proxy)
        online_hash_crackers.append(now)
    if args.submit:
        with open(args.target) as file:
            data = file.read().splitlines()
        data = [i.split(':') for i in data if i.count(':') == 1]
        length = len(data)
        for i, (hashed, result) in enumerate(data):
            if hashlib.md5(result.encode()).hexdigest() == hashed:
                print('%s/%s' % (i, length), hashed, result)
                for cracker in online_hash_crackers:
                    cracker.submit(hashed, result)
    else:
        with open(args.target) as file:
            hashes = set(i.strip() for i in file.read().splitlines())
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
        with open(args.dictionary, 'w') as file:
            file.write('\n'.join(success[i] for i in success))


if __name__ == '__main__':
    main()
