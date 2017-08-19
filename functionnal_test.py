import sys

from node.logic import CacheClient

if __name__ == '__main__':
    _, ip, number_of_tests, purpose = sys.argv
    number_of_tests = int(number_of_tests)

    client = CacheClient(ip)

    if purpose == 'verify':
        for request in range(0, number_of_tests):
            actual = client.get(str(request))
            expected = str(2 * request)
            print('Verifying key=%s, data=%s == %s' % (request, expected, actual))
            assert actual == expected
        print('All done!')
    else:
        for request in range(0, number_of_tests):
            key = str(request)
            data = str(2 * request)
            print('Set key=%s, value=%s' % (key, data))
            client.set(key, data)
        print('Data All set')