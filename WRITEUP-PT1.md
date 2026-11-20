# Custom Intranet, part 1: routing Group JD writup

## Tasks, and member who did them

Tasks:
- Q0/Q1 [Josh]
- Q2 [Josh]
- MyParser.start() [Josh]
- MyIngress.ipv4_forward() [Josh]
- MyIngress.apply() [Dominick]
- MyDeparser.apply() [Dominick]
- Q3 [Dominick]
- Q4 [Dominick]

Each member therefore takes 2 questions and 2 tasks

## Questions and Answers

### 0. What problem does this project solve?
Any host must be able to reach any other host without needing every host to be individually connected to every other host

### 1. List what each host, each switch (s1 to s4) and, in the final option, the controller must know or do so that every host can reach every other host, and give the reason for each. Include the return path. This is your description of the problem space, written before any code or evidence.
> H1
Must know or have:
S1's Port 1 MAC address so that it can send data through it
An IP address so that other hosts can reach it
A default gateway to S1 Port 1 so that it knows to send there instead of elsewhere

> H2
Must know or have:
S1's Port 2 MAC address so that it can send data through it
An IP address so that other hosts can reach it
A default gateway to S1 Port 2 so that it knows to send there instead of elsewhere

>H3
Must know or have:
S2's Port 1 MAC address so that it can send data through it
An IP address so that other hosts can reach it
A default gateway to S2 Port 1 so that it knows to send there instead of elsewhere

>H4
Must know or have:
S2's Port 2 MAC address so that it can send data through it
An IP address so that other hosts can reach it
A default gateway to S2 Port 2 so that it knows to send there instead of elsewhere

>S1
Must know or have:
Rules that map incoming destinations to ports 1-4


>S2
Must know or have:
Rules that map incoming destinations to ports 1-2

>S3
Must know or have:
Rules that map incoming destinations to ports 1-4

>S4
Must know or have:
Rules that map incoming destinations to ports 1-2

### 2. What do you think the reply TTL from h3 to h1 will be and the winning prefix and action for 10.0.3.3, 10.0.3.99 and 10.0.9.99 based on 1-routing/s1-runtime.json? Give your reasons. After step 6, add the evidence you compare them with your make check output. Identify the winning entry for each probe. Why would working pings with only /32 host routes not establish longest-prefix matching?
The reply TTL from h3 to h1 will be 61, as TTL usually starts at 64 and is decreased by one each switch gone through. And h3 would have to travel through 3 switches to reach h1.
For:
- 10.0.3.3
  - The winning prefix will be 32 as that is the prefix matching it in the table
  - The winning action will be forwarding
- 10.0.3.99
  - There is no winning prefix as it does not exist in the table
  - The winning action will be dropping as that is the default action for non-matching
- 10.0.9.99
  - There is no winning prefix as it does not exist in the table
  - The winning action will be dropping as that is the default action for non-matching

### 3. Trace the outgoing Ethernet and IPv4 headers at s1. Which fields change and which stay unchanged? Why must the IPv4 header checksum be recomputed, and why is that a different job from Ethernet's CRC?

### 4. Where does the data plane decide what happens when no destination entry matches. In your program, or in the table's default action? Transfer that reasoning to a table with 192.0.2.0/24 forwarding and 192.0.2.64/26 dropping. What happens to 192.0.2.70, and why? This prefix example is written reasoning, not another network experiment.