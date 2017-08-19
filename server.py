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
        print(element)
        print("Received method: %s" % element.get('method'))
        if element['method'] == 'set':
            socket.send(json.dumps(cache.set(**element['kwargs'])).encode('utf8'))
            continue
        elif element['method'] == 'get':
            socket.send(json.dumps(cache.get(**element['kwargs'])).encode('utf8'))
            continue
        elif element['method'] == 'get_key':
            socket.send(json.dumps(cache.get_key(**element['kwargs'])).encode('utf8'))
            continue
        elif element['method'] == 'set_key':
            socket.send(json.dumps(cache.set_key(**element['kwargs'])).encode('utf8'))
            continue
        elif element['method'] == 'get_nodes':
            socket.send(json.dumps(cache.get_nodes()).encode('utf8'))
            continue
        elif element['method'] == 'add_node':
            cache.add_node(**element['kwargs'])
            socket.send(b"OK")
            continue
        socket.send(b"Ok")
