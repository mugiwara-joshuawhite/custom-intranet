# The Linux equivalent of the learning switch: a bridge that learns MACs itself.
# Given; used by: python3 ../utils/ptfrun.py switching.p4 --ports 3 --linux "sh linux.sh"
# A Linux bridge is also a host: left alone it sends its own IPv6 and multicast
# messages. Those are turned off so only the hosts' frames are on the wire.
ip link del br0 2>/dev/null
ip link add br0 type bridge ageing_time 30000 mcast_snooping 0
sysctl -qw net.ipv6.conf.br0.disable_ipv6=1
ip link set br0 multicast off
for p in veth0 veth2 veth4; do ip link set "$p" master br0; done
ip link set br0 up
