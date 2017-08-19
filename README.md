# Log of development status
### Encountered issues and comments

The development was done in incremental step adding complexity over time.

### First Version

The first version was a distributed cache inside an app:
    - It implements the consistent hashing, the cache stores the uid and instance of each Cache node.
    - Each cache is an instance of class Cache.
    - The Cache class needs to know all nodes in the cache (Set manually like in the tests).
    - The Cache handles (among others) 4 operation:
        - set : This checks the key find the right node and assign the key to it using set_key.
        - get : Equivalent of set, finds the right node and use get_key on it to retrieve it.
        - set_key : This set a key in the cache.
        - get_key : This reads a key from the cache.

The initial tests where implemented on this version, it handles most of the cases for the simplified version of the problem

The idea was that having remote caches would behave the same way, except that the list of nodes needs to be either known in advance or got somehow.
To fit with the requirement that each node needs only know 1 other node, I put this problem aside.

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

The handling for when a node is down was based on the internal Python version, so it's checking that the instance is not None.

This cannot apply to a CacheProxy.

This version is UNDER CONSTRUCTION