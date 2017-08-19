#!/usr/bin/env bash

PORT=5555
COUNTER=1
echo "Starting first node"
python server.py 127.0.0.1:$PORT &
echo "Spawning $1 Nodes"
while [ $COUNTER -ne $1 ]
do
    NEW_PORT=$[$COUNTER+$PORT]
    python server.py 127.0.0.1:$NEW_PORT 127.0.0.1:$PORT &
    COUNTER=$[$COUNTER +1]
done
