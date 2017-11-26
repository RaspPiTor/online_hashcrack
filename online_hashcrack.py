import argparse
import hashlib
import random
import codecs
import re

import requests


class OnlineHashCrack():
    def __init__(self, timeout=3, retry=3,
                 user_agent='OnlineHashCracker', proxy=None):
        self.retry = retry
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = user_agent
        if proxy:
            self.session.proxies = {'http': proxy, 'https': proxy}

    def _fetch(self, _):
        pass

    def get(self, hashed):
        self.session.cookies.clear_expired_cookies()
        for _ in range(self.retry):
            try:
                for result in self._fetch(hashed):
                    if hashlib.md5(result.encode()).hexdigest() == hashed:
                        return result
                    elif result:
                        print('ERROR', result)
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
            try:
                self._submit(hashed, result)
            except requests.exceptions.ReadTimeout as error:
                print(self, 'timed out.')
            except requests.exceptions.ConnectionError:
                print(self, 'failed to connect.')
            except Exception as error:
                print(type(error), error)

    def _submit(self, hashed, result):
        pass


class Nitrxgen(OnlineHashCrack):
    regex = re.compile(r'\$HEX\[([a-f0-9]+)\]')
    
    def __repr__(self):
        return 'Nitrxgen'

    def _fetch(self, hashed):
        r = self.session.get('https://www.nitrxgen.net/md5db/' + hashed,
                               timeout=self.timeout)
        yield r.text
        match = self.regex.fullmatch(r.text)
        if match:
            yield codecs.decode(match.group(1), 'hex').decode('utf-8')


class CrackHash(OnlineHashCrack):
    regex = re.compile(r'\$HEX\[([a-f0-9]+)\]')
    # API is currently under maintanace

    def __repr__(self):
        return 'CrackHash'

    def _fetch(self, hashed):
        r = self.session.get('https://crackhash.com/api.php?hash=' + hashed,
                             timeout=self.timeout)
        yield r.text
        match = self.regex.fullmatch(r.text)
        if match:
            yield codecs.decode(match.group(1), 'hex').decode('utf-8')

    def _submit(self, hashed, result):
        self.session.get('https://crackhash.com/api.php?share=%s&text=%s'
                         % (hashed, result), timeout=self.timeout)


class MD5OVH(OnlineHashCrack):
    regex = re.compile('<html><body>starting<br>'
                       r'Execution time :[0-9]+\.[0-9]+<br>'
                       'value decrypted:(.+)<br>'
                       'value decrypted in hexadecimal:([0-9a-f]+)<br>',
                       re.DOTALL)
    # Cloudflare says website is down

    def __repr__(self):
        return 'MD5OVH'

    def _fetch(self, hashed):
        r = self.session.get('https://www.md5.ovh/index.php?md5=' + hashed,
                             timeout=self.timeout)
        match = self.regex.match(r.text)
        if match:
            yield match.group(1)
            yield codecs.decode(match.group(2), 'hex').decode('utf-8')


class MD5EncryptionDecryption(OnlineHashCrack):
    regex = re.compile('Decrypted Text: </b>(.*)</font>')
    def __repr__(self):
        return 'MD5EncryptionDecryption'

    def _fetch(self, hashed):
        r = self.session.post('http://md5decryption.com/', timeout=self.timeout,
                          data={'submit':'Decrypt+It!', 'hash':hashed})
        match = self.regex.search(r.text)
        if match:
            yield match.group(1)
    def _submit(self, hashed, result):
        self.session.post('http://md5encryption.com/', timeout=self.timeout,
                          data={'submit':'Encrypt+It!', 'word':result})


class MD5DB(OnlineHashCrack):
    def __repr__(self):
        return 'MD5DB'

    def _fetch(self, hashed):
        yield self.session.get('https://md5db.net/api/' + hashed,
                               timeout=self.timeout).text

    def _submit(self, hashed, result):
        self.session.post('https://md5db.net/encrypt/', timeout=self.timeout,
                          data={'submit':'Encrypt+words', 'words':result})


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
    parser.add_argument('-p', '--proxy', help='Use specified proxy.')
    parser.add_argument('-u', '--useragent', default='OnlineHashCracker',
                        help='Useragent to use, default is OnlineHashCracker')
    args = parser.parse_args()
    online_hash_crackers = []
    for cracker in (Nitrxgen, MD5EncryptionDecryption, MD5DB, ):
        now = cracker(timeout=args.timeout, retry=args.retry, proxy=args.proxy,
                      user_agent=args.useragent)
        online_hash_crackers.append(now)
    random.shuffle(online_hash_crackers)
    if args.submit:
        with open(args.target, 'rb') as file:
            data = file.read().decode('utf-8', 'ignore').splitlines()
        data = [i.split(':') for i in set(data) if i.count(':') == 1]
        length = len(data)
        for cracker in online_hash_crackers:
            for i, (hashed, result) in enumerate(data):
                if hashlib.md5(result.encode()).hexdigest() == hashed:
                    try:
                        print('%s/%s  %s %s %s' % (i, length, cracker, hashed,
                                                   result))
                    except UnicodeEncodeError:
                        print('%s/%s %s %s %s' % (i, length, hashed, cracker,
                                               result.encode('utf-8')))
                    cracker.submit(hashed, result)
    else:
        with open(args.target) as file:
            hashes = set(i.strip() for i in file.read().splitlines())
        print('Starting')
        success = {}
        length = len(hashes)
        try:
            for cracker in online_hash_crackers:
                print('Starting', cracker)
                for i, hashed in enumerate(hashes.copy()):
                    random.shuffle(online_hash_crackers)
                    result = cracker.get(hashed)
                    if result is not None:
                        hashes.remove(hashed)
                        success[hashed] = result
                        try:
                            print('%s/%s Success: %s %s %s' %
                                  (i, length, cracker, hashed, result))
                        except UnicodeEncodeError:
                            print('%s/%s Success: %s %s %s' %
                                  (i, length, cracker, hashed,
                                   result.encode('utf-8', 'ignore')))
                        for cracker2 in online_hash_crackers:
                            if cracker != cracker2:
                                cracker2.submit(hashed, result)
                    else:
                        print('%s/%s Failed: %s %s' %
                                  (i, length, cracker, hashed))
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
        with open(args.found, 'wb') as file:
            file.write(b'\n'.join(b':'.join((i.encode(), success[i].encode()))
                                  for i in success))
        with open(args.left, 'w') as file:
            file.write('\n'.join(i for i in hashes if i not in success))
        with open(args.dictionary, 'wb') as file:
            file.write(b'\n'.join(success[i].encode() for i in success))


if __name__ == '__main__':
    main()
