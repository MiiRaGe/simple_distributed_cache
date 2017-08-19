import json
import random
from hashlib import sha1
from bisect import bisect_right

import zmq

REDUNDANCY_SETTING = 1
REQUEST_TIMEOUT = 500
REQUEST_RETRIES = 2


def get_hashed_key(key):
    """
    Returns a integer constructed using the first 8 bytes of the sha1 hash of the key.
    key cannot be anything but string
    :param key:
    :return:
    """
    hashed_key = sha1()
    hashed_key.update(key.encode('utf8'))
    return int(hashed_key.hexdigest()[:8], 16)


def announce_new(new_cache, master_ip):
    """
    This modifies announces new_cache to the master_ip.
    Gets the list of node from the master_ip.
    Then announce the new_cache to the list of nodes in the cluster.
    :param new_cache:
    :param master_ip:
    :return:
    """
    nm = NetworkMessager(master_ip)
    try:
        print('Calling add_node_and_get_nodes')
        nodes = nm.call('add_node_and_get_nodes', **{'ip': new_cache.ip, 'uid': new_cache.uid})
    except AttributeError:
        nm.term()
        return
    print('Got all nodes, announcing to them')
    new_cache.nodes = []
    for node in nodes:
        if node['ip'] == new_cache.ip:
            new_cache.nodes.append((get_hashed_key(new_cache.uid), new_cache))
            continue
        new_cache.nodes.append((get_hashed_key(node['uid']), CacheProxy(node['uid'], node['ip'])))
        if node['ip'] == master_ip:
            continue
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.connect('tcp://%s' % node['ip'])
                socket.send_json({
                    'method': 'add_node',
                    'kwargs': {'ip': new_cache.ip, 'uid': new_cache.uid}
                })
                socket.recv()


class Cache:
    def __init__(self, uuid, ip):
        self.uid = uuid
        self.ip = ip
        self.memory_cache = {}
        self.nodes = [(get_hashed_key(uuid), self)]

    def set(self, key='', data=None):
        """
        Assuming that each node has a list of all accessible nodes.
        Find the first node it's suppose to save the data to
        And apply redundancy on the next REDUNDANCY_SETTING nodes.
        :param key:
        :param value:
        :return:
        """
        origin_index = self.get_next_node_index(key)
        index = origin_index
        redundancy = 0
        while redundancy <= REDUNDANCY_SETTING:
            new_index, node = self.get_next_node(index)
            try:
                node.set_key(key=key, data=data)
                redundancy += 1
            except AttributeError:
                pass
            index = new_index

    def get(self, key=''):
        """
        Get method for the cache cluster, assumes each node has the list of all nodes.
        It finds where the key is supposed to be, then tries to get it as many time as REDUNDANCY_SETTING
        Increasing indexes if it's down.
        It cannot loop infinitely as self is part of the nodes.
        :param key:
        :return:
        """
        origin_index = self.get_next_node_index(key)
        index = origin_index
        redundancy = 0
        while redundancy <= REDUNDANCY_SETTING:
            new_index, node = self.get_next_node(index)
            try:
                return node.get_key(key=key)
            except AttributeError:
                pass
            index = new_index
            redundancy += 1

    def get_next_node(self, index):
        """
        Get the next available node as well as the index of the next one
        It cannot loop infinitely as self is part of the nodes.
        :param index:
        :return:
        """
        node = self.nodes[index][1]
        index += 1
        if index == len(self.nodes):
            index = 0
        return index, node

    def set_key(self, key='', data=None):
        """
        Method to set a an element in the internal cache.
        :param key:
        :param value:
        :return:
        """
        print('\tInner method: set_key')
        self.memory_cache[key] = data

    def get_key(self, key=''):
        """
        Method to get a element from the internal dict acting as cache.
        :param key:
        :return:
        """
        print('\tInner method: get_key')
        return self.memory_cache.get(key)

    def get_next_node_index(self, key):
        """
        Assuming attribute nodes is a list of sorted (rank, Cache)
        It uses bisect to find the first one bigger than indexed_key.
        It does not handle the case when rank == indexed_key as it's using tuple comparison
        never expecting the first key to be equal (python default to second key, which is not sortable)
        :param key:
        :return:
        """
        indexed_key = get_hashed_key(key)
        index = bisect_right(self.nodes, (indexed_key, 0))
        return index if index != len(self.nodes) else 0

    def get_nodes(self):
        return [{'uid': x.uid, 'ip': x.ip} for _, x in self.nodes]

    def add_node(self, uid=None, ip=''):
        """
        Adds a node from the outside to the internal list
        :param uid:
        :param ip:
        :return:
        """
        self.nodes.append((get_hashed_key(uid), CacheProxy(uid, ip)))
        self.nodes.sort(key=lambda x: x[0])


class NetworkMessager:
    def __init__(self, ip):
        self.ip = ip
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect('tcp://%s' % ip)
        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)
        self.retry_timeout = REQUEST_TIMEOUT

    def _change_ip(self, ip):
        """
        Set the ip to a random node in the cluster so that request are spread sort of evenly.
        :return:
        """
        self.ip = ip
        self.socket.close()
        try:
            self.poll.unregister(self.socket)
        except KeyError:
            pass
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect('tcp://%s' % ip)
        self.poll.register(self.socket, zmq.POLLIN)

    def call(self, method, **kwargs):
        print('\tRemote method: %s' % method)
        retries_left = REQUEST_RETRIES
        request = {
            'method': method,
            'kwargs': kwargs
        }
        try:
            while retries_left:
                self.socket.send_json(request)
                expect_reply = True
                while expect_reply:
                    socks = dict(self.poll.poll(self.retry_timeout))
                    if socks.get(self.socket) == zmq.POLLIN:
                        return self.socket.recv_json()
                    else:
                        self.socket.close()
                        self.poll.unregister(self.socket)
                        retries_left -= 1
                        if retries_left == 0:
                            break
                        # Create new connection
                        self.socket = self.context.socket(zmq.REQ)
                        self.socket.connect('tcp://%s' % self.ip)
                        self.poll.register(self.socket, zmq.POLLIN)
                        self.socket.send_json(request)
        except zmq.ZMQError:
            pass
        # Mimic the case where Cache is None locally, cally cache.get_key would through attibute error
        raise AttributeError

    def term(self):
        self.socket.close()
        try:
            self.poll.unregister(self.socket)
        except KeyError:
            pass


class CacheProxy(NetworkMessager):
    """
    Proxy for the Cache object
    There's no differences in behaviour between local and remote cache.
    """

    def __init__(self, uid, ip):
        self.uid = uid
        super().__init__(ip)

    def set_key(self, **kwargs):
        return self.call('set_key', **kwargs)

    def get_key(self, **kwargs):
        return self.call('get_key', **kwargs)

    def add_node(self, **kwargs):
        return self.call('add_node', **kwargs)


class CacheClient(NetworkMessager):
    def __init__(self, ip):
        super().__init__(ip)
        self.retry_timeout = 2500

    def set(self, key, data):
        retries = 0
        while retries <= REQUEST_RETRIES:
            try:
                self.call('set', key=key, data=data)
                return
            except AttributeError:
                pass
            retries += 1

    def get(self, key):
        retries = 0
        while retries <= REQUEST_RETRIES:
            try:
                return self.call('get', key=key)
            except AttributeError:
                pass
            retries += 1
