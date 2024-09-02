# Load balancers are not a best practice for SC4S
In syslog ingestion systems load balancers are usually used for horizontal scaling and high availability.

It is a best practice to avoid load balancing in both cases. Instead of horizontal scaling it is recommended use a robust, single server. For high availability choose rather a shared-IP cluster.

While neither recommended nor supported, the usage of LBs is still popular among SC4S users. This section of documentation discusses various LB solutions and their possible setups together with well known issues.

## General considerations regarding load balancers
While using load balancers it's recommended to:
- Preserve the actual source IP of the sending machine. The default behavior of L4 LBs is to overwrite the source IP from the client’s IP to their own.
- For high availability use the LB solution with HA mode

Load balancing setup differs for TCP/TLS and UDP.

For TCP/TLS:
- There are two ways of preserving the source IP: using the "PROXY" protocol or IP transparency (DNAT configuration)
- For the "PROXY" configuration make sure to enable it on the SC4S side with  `SC4S_SOURCE_PROXYCONNECT=yes`
- TCP/TLS load balancers do not consider the weight of individual connection load and are frequently biased to one instance. Vertically scale all members in a single resource pool to accommodate the full workload

For UDP:
- Load balancers for UDP can only use DNAT, for example with DSR (Direct Server Response)