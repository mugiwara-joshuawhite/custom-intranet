# The Linux equivalent of R1: a router with a GRE tunnel to R2. Given.
# Used by: python3 ../utils/ptfrun.py tunnel.p4 --ports 2 --linux "sh linux.sh"
# veth0 is port 0 (A's network), veth2 is port 1 (the Internet).
set -e
if ! ip link add gre-probe type gre local 192.0.2.1 remote 192.0.2.2 2>/dev/null; then
    echo "This computer's Linux kernel has no GRE support loaded, so the Linux tunnel cannot be built."
    echo "On a Linux computer, outside the container, run:  sudo modprobe ip_gre"
    echo "then start the container again and rerun. Your P4 tunnel's own tests do not need this."
    exit 1
fi
ip link del gre-probe
sysctl -qw net.ipv4.ip_forward=1
sysctl -qw net.ipv4.conf.all.rp_filter=0
ip link set veth0 address 00:00:00:00:01:00
ip link set veth2 address 00:00:00:00:02:00
ip addr add 10.1.0.1/24 dev veth0
ip addr add 203.0.113.1/24 dev veth2
ip neigh replace 10.1.0.5 lladdr 00:00:00:00:00:05 dev veth0 nud permanent
ip neigh replace 203.0.113.254 lladdr 00:00:00:00:02:fe dev veth2 nud permanent
ip route add 198.51.100.2/32 via 203.0.113.254 dev veth2
ip tunnel add gre1 mode gre local 203.0.113.1 remote 198.51.100.2 ttl 64
sysctl -qw net.ipv6.conf.gre1.disable_ipv6=1 2>/dev/null || true
ip link set gre1 up
ip route add 10.2.0.0/16 dev gre1
for d in veth0 veth2 gre1; do sysctl -qw net.ipv4.conf.$d.rp_filter=0; done
