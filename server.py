import json
import zmq
import sys

from uuid import uuid4

from node.logic import Cache


if __name__ == '__main__':
    ip = sys.argv[1]
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    address = "tcp://%s" % ip
    print('Listening to: %s' % address)
    socket.bind(address)

    cache = Cache(str(uuid4()), ip)
    try:
        master_ip = sys.argv[2]
        if ip != master_ip:
            print('Announcing self to master ip: %s' % master_ip)
            cache.announce_new(master_ip)
    except IndexError:
        pass

    while True:
        element = socket.recv_json()
        print("Received method: %s" % element.get('method'))
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
        socket.send(b"Ok")
