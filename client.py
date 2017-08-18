import json
import zmq

#  Prepare our context and sockets
context = zmq.Context()
socket = context.socket(zmq.REQ)
address = "tcp://localhost:5560"
socket.connect(address)

print('Sending request to %s' % address)
#  Do 10 requests, waiting each time for a response
for request in range(1, 11):
    socket.send(json.dumps({'method': 'set', 'kwargs': {'key': 'key%s' % request, 'data': 'Data%s' % request}}).encode('utf8'))
    message = socket.recv()
    print("Received reply %s [%s]" % (request, message))

for request in range(1, 11):
    socket.send(json.dumps({'method': 'get', 'kwargs': {'key': 'key%s' % request}}).encode('utf8'))
    message = socket.recv()
    print("Received reply %s [%s]" % (request, message))
