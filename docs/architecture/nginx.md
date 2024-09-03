# Nginx
While load balancing syslog with NGINX Open Source is neither recommended, nor supported by Splunk, it is still a "good enough" solution for some customers.

Note the main disadvantages of Nginx Open Source:
- Due to no High Availability an Nginx LB becomes a new single point of failure.
- Even with the round-robin we also often observe bias in traffic distribution which results in overloading some of the instances in the pool. This results in growing queues, which lead to delays, data drops and memory and disk issues.
- Nginx Open Source doesn't provide active health checking, which is crucial for UDP DSR (Direct Server Return) load balancing.

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

## Preserving source IP
| Method                     | Protocol   |
|----------------------------|------------|
| PROXY protocol             | TCP/TLS    |
| Transparent IP             | TCP/TLS    |
| Direct Server Return (DSR) | UDP        |

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
| Receiver                   | Performance                   |
|----------------------------|-------------------------------|
| Single SC4S Server         | 4,341,000 (71,738.98 msg/sec) |
| Load Balancer + 2 Servers  | 5,996,000 (99,089.03 msg/sec) |


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

4. Make sure to disable `Source/Destination Checking` on your LB's host if you work on AWS

### Test your setup
1. Send UDP messages to the load balancer and ensure that they are being correctly received in Splunk with the correct host IP:
```bash
echo "hello world" > /dev/udp/<LB_IP>/514
```

2. Run performance tests

| Receiver / Drops Rate for EPS (msgs/sec) | 4,500  | 9,000  | 27,000 | 50,000 | 150,000 | 300,000 |
|------------------------------------------|--------|--------|--------|--------|---------|---------|
| Single SC4S Server                       | 0.33%  | 1.24%  | 52.31% | 74.71% |    --   |    --   |
| Load Balancer + 2 Servers                | 1%     | 1.19%  | 6.11%  | 47.64% |    --   |    --   |
| Single Finetuned SC4S Server             | 0%     | 0%     | 0%     | 0%     |  47.37% |    --   |
| Load Balancer + 2 Finetuned Servers      | 0.98%  | 1.14%  | 1.05%  | 1.16%  |  3.56%  |  55.54% |