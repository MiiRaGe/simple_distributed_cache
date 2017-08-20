import os
import zmq
import sys

from uuid import uuid4
from collections import deque

from node.logic import Cache, announce_new

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        ip = sys.argv[1]
    else:
        ip = os.environ.get('ZMQ_IP')
    if not ip:
        print('You must give an ip argument or set ZMQ_IP environment variable')
        exit()

    cache = Cache(str(uuid4()), ip)
    pending_write_queue = deque()
    try:
        if len(sys.argv) >= 3:
            master_ip = sys.argv[2]
        else:
            master_ip = os.environ.get('ZMP_MASTER')
        if master_ip and ip != master_ip:
            print('Announcing self to master ip: %s' % master_ip)
            announce_new(cache, master_ip)

    except (IndexError, zmq.ZMQError):
        pass

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    address = "tcp://%s" % ip
    print('Listening to: %s' % address)
    socket.bind(address)

    while True:
        element = socket.recv_json()
        print("%s: Received method: %s" % (ip, element.get('method')))
        if element['method'] == 'set':
            socket.send_json(cache.set(**element['kwargs']))
            continue
        elif element['method'] == 'get':
            socket.send_json(cache.get(**element['kwargs']))
            continue
        elif element['method'] == 'get_key':
            socket.send_json(cache.get_key(**element['kwargs']))
            continue
        elif element['method'] == 'set_key':
            if cache.status == 'JOINING':
                pending_write_queue.append(element['kwargs'])
                socket.send_json(None)
            else:
                socket.send_json(cache.set_key(**element['kwargs']))
            continue
        elif element['method'] == 'add_node_and_get_nodes':
            cache.add_node(**element['kwargs'])
            socket.send_json(cache.get_nodes())
            continue
        elif element['method'] == 'get_nodes':
            socket.send_json(cache.get_nodes())
            continue
        elif element['method'] == 'add_node':
            cache.add_node(**element['kwargs'])
            socket.send(b"OK")
            continue
        elif element['method'] == 'get_keys':
            socket.send_json(list(cache.memory_cache.keys()))
        elif element['method'] == 'update_node':
            cache.update_node(**element['kwargs'])
            socket.send(b"OK")
            continue
        elif element['method'] == 'get_values':
            socket.send_json(cache.get_values(**element['kwargs']))
            continue
        socket.send(b"Unknown Method")
