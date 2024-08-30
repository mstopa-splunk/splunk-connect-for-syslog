# Nginx
While using a bare Nginx load balancing is neither a recommended, nor a supported solution, it is still a "good enough" solution for some customers.

It is a free and open source solution, well documented and with a big and active community of users.
The open source version of Nginx doesn't provide High Availability, so in fact an nginx LB becomes a new single point of failure. Even with the round-robin we also often observe bias in traffic distribution which results in overloading some of the instances in the pool. As the result customers report memory and disk issues, growing queues and delays in processing.

## Preserving source IP
| Method                     | Protocol   |
|----------------------------|------------|
| PROXY protocol             | TCP/TLS    |
| Transparent IP             | TCP/TLS    |
| Direct Server Return (DSR) | UDP        |

## Install Nginx
1. Refer to Nginx documentation for instructions on installing Nginx **with the stream module**, which is necessary for TCP/UDP load balancing. For example on Ubuntu:
```bash
sudo apt update
sudo apt -y install nginx libnginx-mod-stream
```

2. In the main Nginx configuration update `events` section to increase performance, for example:
`/etc/nginx/nginx.conf`
```conf
events {
    worker_connections 20480;
    multi_accept on;
    use epoll;
}
```

## Option 1: Configure Nginx with the PROXY protocol
Advantages:
- easy to set up

Disadvantages:
- worse performance
- available only for TCP/TLS, not available for UDP
- overwriting the source IP in syslog-ng is not ideal. SOURCEIP is a hard macro and only HOST can be overwritten
- overwriting the source IP is available only in SC4S>3.4.0

1. On your LB node add a configuration similar to the following:
`/etc/nginx/modules-enabled/sc4s.conf`
```conf
stream {
    # Define upstream for each of SC4S hosts and ports
    # Default SC4S TCP ports are 514, 601, 5425, 6514
    # Include also your custom ports
    upstream stream_syslog_514 {
        server <SC4S_IP_1>:514;
        server <SC4S_IP_2>:514;
    }
    upstream stream_syslog_601 {
        server <SC4S_IP_1>:601;
        server <SC4S_IP_2>:601;
    }
    upstream stream_syslog_5425 {
        server <SC4S_IP_1>:5425;
        server <SC4S_IP_2>:5425;
    }
    upstream stream_syslog_6514 {
        server <SC4S_IP_1>:6514;
        server <SC4S_IP_2>:6514;
    }

    # Define a common configuration block for all servers
    map $server_port $upstream_name {
        514   stream_syslog_514;
        601   stream_syslog_601;
        5425  stream_syslog_5425;
    }

    # Define a virtual server for each upstream connection
    # make sure to set 'proxy_protocol' to 'on'
    server {
        listen        514;
        listen        601;
        listen        5425;
        proxy_pass    $upstream_name;
        
        proxy_timeout 3s;
        proxy_connect_timeout 3s;
        
        proxy_protocol on;
    }

    server {
        listen        6514;
        proxy_pass    stream_syslog_6514;
        
        proxy_timeout 3s;
        proxy_connect_timeout 3s;
        
        proxy_protocol on;
        
        proxy_ssl on;
    }
}
```
3. Refer to Nginx documentation to find the command to reload the service, for example `sudo nginx -s reload`.
4. Add the following parameter to SC4S configuration and restart your instances:
`/opt/sc4s/env_file`
```conf
SC4S_SOURCE_PROXYCONNECT=yes
```

### Test your setup
1. Send TCP/TLS messages to the load balancer and ensure that they are being correctly received in Splunk with the correct host IP:
```bash
echo "hello world" | netcat <LB_IP> 514
```

2. Run performance tests based on [Check TCP Performance](tcp_performance_tests.md)
| Receiver       | Same Subnet                   | WAN                            |
|----------------|-------------------------------|--------------------------------|
| Server 1       | 4,410,000 (72,879.48 msg/sec) | 4,280,000 (70,726.90 msg/sec)  |
| Server 2       | 4,341,000 (71,738.98 msg/sec) | 4,255,000 (70,316.86 msg/sec)  |
| Load Balancer  | 5,996,000 (99,089.03 msg/sec) | 6,046,000 (99,917.23 msg/sec)  |


## Option 2: Configure Nginx with DSR (Direct Server Return)
Advantages:
- works for UDP
- more efficient (saves one hop)

Disadvantages:
- DSR setup requires active health checks, because LB cannot expect responses from the upstream. Active health checks are not available in Nginx open source. Switch to Nginx Plus or implement your own active health checking
- requires superuser privileges
- for cloud users might require disabling Source/Destination Checking (tested with AWS)

1. In the main Nginx configuration update `user` to root, for example:
`/etc/nginx/nginx.conf`
```conf
user root;
```

2. Add a configuration similar to the following:
`/etc/nginx/modules-enabled/sc4s.conf`
```conf
stream {
    # Define upstream for each of SC4S hosts and ports
    # Default SC4S UDP port is 514
    # Include also your custom ports
    upstream stream_syslog_514 {
        server <SC4S_IP_1>:514;
        server <SC4S_IP_2>:514;
    }

    # Define connections to each of your upstreams.
    # Make sure to include `proxy_bind` and `proxy_responses 0`.
    server {
        listen        514 udp;
        proxy_pass    stream_syslog_514;
        
        proxy_bind $remote_addr:$remote_port transparent;
        proxy_responses 0;
    }
}
```

3. Refer to Nginx documentation to find the command to reload the service, for example `sudo nginx -s reload`.

4. Make sure to disable `Source/Destination Checking` if you work on AWS

### Test your setup
1. Send UDP messages to the load balancer and ensure that they are being correctly received in Splunk with the correct host IP:
```bash
echo "hello world" > /dev/udp/<LB_IP>/514
```

2. Run performance tests
| Receiver       | Maximum EPS without drops |
|----------------|---------------------------|
| Server 1       |                           |
| Server 2       |                           |
| LB             |                           |