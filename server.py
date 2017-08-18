import json
import zmq
import sys

from uuid import uuid4

from node.logic import Cache


if __name__ == '__main__':
    port = sys.argv[1]
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    address = "tcp://localhost:%s" % port
    print('Listening to: %s' % address)
    socket.connect(address)

    cache = Cache(str(uuid4()), address)

    while True:
        print(socket)
        message = socket.recv()
        print("Received request: %s" % message)

        element = json.loads(message)
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
        elif element['method'] == 'announce':
            print('Not implemented yet')
            pass
        socket.send(b"Ok")
