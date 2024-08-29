# Architectural Considerations

Building a performant, HA, performant and scalable syslog ingestion system is a non-trivial task.

The syslog protocol design prioritizes speed and efficiency, which can occur at the expense of resiliency and reliability. Because of these tradeoffs, traditional methods to provide scale and resiliency do not necessarily transfer to syslog.

## Syslog Architecture recommendations
The following subsections provide recommendations and suggestions for planning your syslog ingestions system based on SC4S.

### Recommended system design sequence
1. Locate your SC4S server
2. Choose your optimal hardware setup
3. Fine-tune your SC4S instance
4. Monitor and troubleshoot
5. Build a high-availability architecture

#### Locate your SC4S server
Syslog is a "send and forget" protocol snf iy does not perform well when routed through substantial network infrastructure.

For centrally located syslog servers we often observe both UDP and TCP traffic problems and data loss.

Instead, provide for edge collection. Keep the client and server ideally a few - optimally one - hop away from each other. Syslog should not pass a WAN and the chance of a failure increaces with the number of Layer 4 devices in the path, including TCP/UDP load balancers.

#### Choose your optimal hardware setup
Hardware specification is the crucial part of designing a performant syslog ingestion system. See [Choose Your Hardware Setup](hardware.md).

#### Choose between UDP and TCP and fine-tune SC4S
While UDP is the protocol traditionally recommended for syslog, TCP is also an option provided by the standard and many vendors.

UDP reduces network load on the network stream with no required receipt verification or window adjustment. TCP uses Acknowledgement Signals (ACKS) to avoid data loss, however, loss can still occur, when:

* The TCP session is closed: Events published while the system is creating a new session are lost. 
* The remote side is busy and cannot send an acknowledgement signal fast enough: Events are lost due to a full local buffer.
* A single acknowledgement signal is lost by the network and the client closes the connection: Local and remote buffer are lost.
* The remote server restarts for any reason: Local buffer is lost.
* The remote server restarts without closing the connection: Local buffer plus timeout time are lost.
* The client side restarts without closing the connection.
* Increased overhead on the network can lead to loss.

You can for example use TCP only if the syslog event is larger than the maximum size of the UDP packet on your network (typically limited to Web Proxy, DLP, and IDs type sources).

Depending on your choice you should check some or all of the following subsections:
- [Check UDP Performance]("architecture/udp_performance_tests.md")
- [Finetuning for UDP]("architecture/finetuning_for_udp.md")
- [Check TCP Performance]("architecture/tcp_performance_tests.md")
- [Finetuning for TCP]("architecture/finetuning_for_tcp.md")

#### Avoid load balancers in front of SC4S
It is common to see syslog designs with various load balancers distributing traffic to multiple SC4S instances.

We are aware of the popularity of this solution. We document best practices related to load balancers in the [Load Balancers](architecture/lb.md) section, as well as requirements and challenges related to load balancing syslog.

However, Splunk does not support architectures utilizing load balancers for scaling.

As a best practice, do not co-locate syslog servers for horizontal scale and do not load balance to them with a front-side load balancer. Instead, make sure that every SC4S instance in your HA cluster can accomodate the full workload.

For the reasons behind see the [Load Balancers](architecture/lb.md) section.

#### Monitor and troubleshoot

#### Build a high-availability architecture
Load balancing for high availability does not work well for stateless, unacknowledged syslog traffic. More data is preserved when you use a more simple design such as vMotioned VMs.  With syslog, the protocol itself is prone to loss, and syslog data collection can be made "mostly available" at best.