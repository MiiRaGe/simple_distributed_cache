from uuid import uuid4

import mock
import random
from unittest import TestCase

from node.logic import Cache, get_hashed_key


class SingleClusterCache(TestCase):
    def setUp(self):
        self.cache = Cache(0)
        self.cache.nodes = [(0, self.cache)]

    def test_get_non_existing_key(self):
        assert self.cache.get('foo') is None

    def test_set_and_get_key(self):
        self.cache.set('foo', 'bar')
        assert self.cache.get('foo') == 'bar'

    def test_set_multiple_keys(self):
        self.cache.set('foo', 'bar')
        self.cache.set('foo1', 'bar1')
        self.cache.set('foo2', 'bar2')
        assert self.cache.get('foo') == 'bar'
        assert self.cache.get('foo1') == 'bar1'
        assert self.cache.get('foo2') == 'bar2'


class MultipleClusterCache(TestCase):
    def setUp(self):
        self.caches = [Cache(str(uuid4())) for x in range(0, 10)]
        self.servers = sorted([(get_hashed_key(cache.id), cache) for cache in self.caches])
        for cache in self.caches:
            cache.nodes = self.servers
            cache.memory_cache = dict()

    @property
    def cache(self):
        """
        This also test that the actions can be taken on any node
        :return:
        """
        return random.choice([x for x in self.caches if x is not None])

    def test_get_non_existing_key(self):
        assert self.cache.get('foo') is None

    def test_set_and_get_key(self):
        self.cache.set('foo', 'bar')
        assert self.cache.get('foo') == 'bar'

    def test_set_multiple_keys(self):
        self.cache.set('foo', 'bar')
        self.cache.set('foo1', 'bar1')
        self.cache.set('foo2', 'bar2')
        assert self.cache.get('foo') == 'bar'
        assert self.cache.get('foo1') == 'bar1'
        assert self.cache.get('foo2') == 'bar2'

    @mock.patch('node.logic.REDUNDANCY_SETTING', new=1)
    def test_set_multiple_keys_with_1_node_down(self):
        """
        It uses the fact that the self.servers is a reference so that all cache instance
        have 1 node down.
        It's harder to reproduce with this implementation as normally the server would just
        not respond
        :return:
        """
        datas = [('foo%s' % x, 'bar%s' % x) for x in range(0, 30)]
        for key, value in datas:
            self.cache.set(key, value)

        index_to_down = random.randint(0, len(self.caches))
        self.servers[index_to_down] = (self.servers[index_to_down][0], None)

        for key, value in datas:
            assert self.cache.get(key) == value

    @mock.patch('node.logic.REDUNDANCY_SETTING', new=2)
    def test_set_multiple_keys_with_2_node_down(self):
        """
        It uses the fact that the self.servers is a reference so that all cache instance
        have 2 node downs.
        :return:
        """
        datas = [('foo%s' % x, 'bar%s' % x) for x in range(0, 30)]
        for key, value in datas:
            self.cache.set(key, value)

        indexes_to_down = random.sample([x for x in range(0, len(self.caches))], 2)
        for index in indexes_to_down:
            self.servers[index] = (self.servers[index][0], None)

        for key, value in datas:
            assert self.cache.get(key) == value


class FourNodeTwoConsecutiveDown(TestCase):
    @mock.patch('node.logic.REDUNDANCY_SETTING', new=2)
    @mock.patch('node.logic.get_hashed_key')
    def test_regression_key_not_found(self, get_hashed_key):
        caches = [Cache(0) for x in range(0, 4)]
        nodes = [(i, c) for i, c in enumerate(caches)]
        for cache in caches:
            cache.nodes = nodes
        # Set this to 5 so the next node is 0
        get_hashed_key.return_value = 5
        caches[0].set('foo', 'bar')
        assert caches[0].memory_cache['foo'] == 'bar'
        assert caches[1].memory_cache['foo'] == 'bar'
        assert caches[2].memory_cache['foo'] == 'bar'
        assert not 'foo' in caches[3].memory_cache
        nodes[0] = (0, None)
        nodes[1] = (1, None)
        for cache in caches:
            cache.nodes = nodes
        assert caches[3].get('foo') == 'bar'
        assert not caches[3].memory_cache