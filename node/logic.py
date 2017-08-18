from hashlib import sha1
from bisect import bisect_right

REDUNDANCY_SETTING = 1


class Cache:
    nodes = []

    def __init__(self, uuid):
        self.id = uuid
        self.memory_cache = {}

    def set(self, key, value):
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
            node.set_key(key, value)
            if new_index == origin_index:
                break
            index = new_index
            redundancy += 1

    def get_next_node(self, index):
        """
        Get the next available node as well as the index of the next one
        It cannot loop infinitely as self is part of the nodes.
        :param index:
        :return:
        """
        while self.nodes[index][1] is None:
            index += 1
            if index == len(self.nodes):
                index = 0
        node = self.nodes[index][1]
        index += 1
        if index == len(self.nodes):
            index = 0
        return index, node

    def get(self, key):
        """
        Get method for the cache cluster, assumes each node has the list of all nodes.
        It finds where the key is supposed to be, then tries to get it as many time as REDUNDANCY_SETTING
        Increasing indexes of the node if it's down (None for this scenario).
        It cannot loop infinitely as self is part of the nodes.
        :param key: 
        :return: 
        """
        origin_index = self.get_next_node_index(key)
        index = origin_index
        result = None
        redundancy = 0
        while result is None and redundancy <= REDUNDANCY_SETTING:
            new_index, node = self.get_next_node(index)
            result = node.get_key(key)
            if new_index == origin_index:
                break
            index = new_index
            redundancy += 1
        return result

    def set_key(self, key, value):
        """
        Method to set a an element in the internal cache.
        :param key:
        :param value:
        :return:
        """
        self.memory_cache[key] = value

    def get_key(self, key):
        """
        Method to get a element from the internal dict acting as cache.
        :param key:
        :return:
        """
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
