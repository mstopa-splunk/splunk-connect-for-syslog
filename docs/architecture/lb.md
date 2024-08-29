* Attempting to load balance for scale can cause more data loss due to normal device operations
and attendant buffer loss. A simple, robust single server or shared-IP cluster provides the best performance.
* Front-side load balancing causes inadequate data distribution on the upstream side, leading to uneven data load on the indexers.