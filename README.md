# Log of development status

## Encountered issues and comments

The development was done in incremental step adding complexity over time.

Here is a summary of what's in:
  - It's in python 3.5
  - The node.logic.CacheClient(ip) supports get and set
  - server.py runs a zmq server, it needs 2 cmd line argument or environment variables:
    * python server.py <binding_ip> <any_other_node>
    * ZMQ_IP = binding_ip
    * ZMQ_MASTER = ip of any other node
  - The cluster can lose 1 node without loosing data
  - Crude tests only the local cache with multiple local cache instances.
    * It misses unit test for the proxy and network methods.
  - Any one need only need the ip of another node
  - ZeroMQ was used for communicatioin
  - Every Node can be potentially used by the client
  - The nodes can be run with docker

What's missing:
  - More unit tests
  - Nodes can be added and removed without any downtime.
    * With the implementation I went for, this would have taken quite a bit of work I think, so I decided to keep it when I'm somewhat satisfied with the rest. Didn't have time to do it in the end.
  
Comments:
  - In theory the project would benefit from a load balancer between client and nodes to spread out the work, so that a node doesn't die for request while the other are fine.
  - I've encounter a few volatile bug that I did not managed to fix, so it might be unstable.
  - The usage of ZeroMQ is probably crude, I pick it up as I went.
  - The implementation of consistent hashing isn't optimized.
    * It's using binary search on a sorted list and circle around the index "manually"
    but we could use a more adapted structure, something when circling is convenient and adding/removing/finding is optimal

## Running nodes

    docker build -t cache_node .
    docker network create --subnet=172.18.0.0/16 cache_cluster
To run 4 node:

    docker run -e ZMQ_IP=172.18.0.2:5555 -e ZMP_MASTER=172.18.0.2:5555 --net cache_cluster --ip 172.18.0.2 -P -it cache_node
    docker run -e ZMQ_IP=172.18.0.3:5555 -e ZMP_MASTER=172.18.0.2:5555 --net cache_cluster --ip 172.18.0.3 -P -it cache_node 
    docker run -e ZMQ_IP=172.18.0.4:5555 -e ZMP_MASTER=172.18.0.3:5555 --net cache_cluster --ip 172.18.0.4 -P -it cache_node 

## Development Stages

### First Version (POC)

The first version was a distributed cache inside an app:
  - It implements the consistent hashing, the cache stores the uid and instance of each Cache node in a sorted list.
  - Each cache is an instance of class Cache.
  - The Cache class needs to know all nodes in the cache (Set manually like in the tests).
  - The Cache handles (among others) 4 operation:
    - set : This checks the key find the right node and assign the key to it using set_key.
    - get : Equivalent of set, finds the right node and use get_key on it to retrieve it.
    - set_key : This set a key in the cache.
    - get_key : This reads a key from the cache.

The initial tests where implemented on this version, it handles most of the cases for the simplified version of the problem

The idea was that having remote caches would behave the same way except:
  - The list of nodes needs to be obtain somehow.
  - Each set_key and get_key operation is identical except it's remote.

To fit with the requirement that each node needs only know 1 other node, I put this problem aside for the initial version.

### Second Version

The second version introduced the client/server concept:
  - A server instance has an instance of the class Cache
  - A server maps a json message containing a method and arguments to the corresponding method of the Cache instance
  - A client connects to the server and send a few set/get and assert the result is correct.

That version was to add the remote client/server concept but also learn about ZeroMQ api.

### Third Version

To achieve the distributed version of the cache, you need to have all the functionnality of the first version adding the possibility for
 a Cache instance to be remote.

The third version introduced a CacheProxy:
  - A CacheProxy hold an uid, an ip and a socket.
  - It implements the set_key and get_key methods that would be called by another node in order to save the data.
  - The list of 'uid', 'ip' needs to be set manually for each node.
  - The server can also receive set_key and get_key method.

With this, each node can handle any request, a client can connect to any node and do any set/get operation successfully.

Since the interface of the CacheProxy is identical as the Cache, the tests are still passing, and remains somewhat valid (excludes the whole network aspect that isn't tested)

### Fourth Version

Among the remaining issues, knowing other nodes in the cluster is problematique.

The fourth version introduced 3 new methods on each Cache and server:
  - Each Cache now only needs 1 "master" ip. (using master for clarity but could be any node in theory)
  - A Cache instance has a announce_new method. (it registers in the master list of nodes and gets the list of nodes from master)
  - Once the Cache instance got the list of nodes from master it announces itself to the whole list.
  - This introduces a problem of concurrency if 2 nodes come alive at the same time with a different master.

I assumed for the sake of the exercise that spawning a new node would either always use the same "master" ip,

Or that the control would give sufficient time for nodes and cluster to be have their internal node list synchronised.

For this version I created a script that would spawn 20 nodes.

A test script then assert:
  - Every node have the same internal node list.
  - A random node is picked from the list and a random operation (get or set) is done on it.
  - It does n number of operations, either setting data or asserting the data set is correct
  - The keys are random and so is the data.

### Fifth Version

In the first version the handling for when a node is down was based on the internal Python version, so it's checking that the instance is not None.
This cannot apply to a CacheProxy.

Changes:
  - Some request changes to polling with timeout to prevent hanging when a node is down.
  - It raises an attribute error when network fails so that it behave like calling .set_key on None.
  - Added Dockerfile, although it's very crude.
  - Changed the functionnal test file so it's easier to load and verify data

Tried a randomize node for the client by getting the list of nodes from a node and randomize which node is reached, but that doesn't work well when nodes are in an internal network and client needs to know external IP not internal.