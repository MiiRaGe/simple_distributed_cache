import json
import random
import sys

from uuid import uuid4

import zmq


if __name__ == '__main__':
    ip = sys.argv[1]
    number_of_tests = 100
    if len(sys.argv) == 3:
        number_of_tests = int(sys.argv[2])
    #  Prepare our context and sockets
    with zmq.Context() as context:
        with context.socket(zmq.REQ) as socket:
            address = "tcp://%s" % ip
            print('Connecting to one node')
            socket.connect(address)
            print('Getting the list of nodes')
            socket.send_json({'method': 'get_nodes'})
            nodes = socket.recv_json()

    print('Preparing the socket for all nodes of network')
    data = {}
    sockets = []
    for node in nodes:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://%s" % node['ip'])
        sockets.append(socket)

    print('Asserting nodes are consistent')
    for socket in sockets:
        socket.send_json({'method': 'get_nodes'})
        new_nodes = socket.recv_json()
        try:
            assert new_nodes == nodes
        except:
            set1 = {(x['uid'], x['ip']) for x in new_nodes}
            set2 = {(x['uid'], x['ip']) for x in nodes}
            if len(set1) > len(set2):
                print('Slave node knows best')
                print(set1-set2)
            else:
                print('Master node knows best')
                print(set2-set1)
            raise

    print('Generating random %s requests' % number_of_tests)
    for request in range(0, number_of_tests):
        socket = random.choice(sockets)
        if not data:
            operation = 'set'
        else:
            operation = 'set' if random.getrandbits(1) else 'get'
        if operation == 'set':
            random_key = str(uuid4())
            random_data = random.getrandbits(16)
            data[random_key] = random_data
            print('Set key=%s, value=%s' % (random_key, random_data))
            socket.send_json({'method': 'set', 'kwargs': {'key': random_key, 'data': random_data}})
            socket.recv()
        else:
            key = random.choice(list(data.keys()))
            print('Get key=%s' % key)
            socket.send_json({'method': 'get', 'kwargs': {'key': key}})
            received_data = socket.recv_json()
            try:
                assert received_data == data[key]
            except:
                print('%s request FAILED' % request)
                print(received_data, data[key])
                raise
