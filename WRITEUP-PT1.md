# Custom Intranet, part 1: routing Group JD writup

## Tasks, and member who did them

Tasks:
- Q0/Q1
- Q2
- MyParser.start()
- MyIngress.ipv4_forward()
- MyIngress.apply()
- MyDeparser.apply()
- Q3
- Q4

Each member therefore takes 2 questions and 2 tasks

## Questions and Answers

### 0. What problem does this project solve?
Any host must be able to reach any other host without needing every host to be individually connected to every other host

### 1. List what each host, each switch (s1 to s4) and, in the final option, the controller must know or do so that every host can reach every other host, and give the reason for each. Include the return path. This is your description of the problem space, written before any code or evidence.
> H1
Must know S1's address

> H2
Must know S1's address

>H3
Must know S2's address

>H4
Must know S2's address

>S1
Must know S3's address
Must know S4's address

>S2
Must know S3's address
Must know S4's address

>S3
Must know S1's address
Must know S2's address

>S4
Must know S1's address
Must know S2's address

### 2. What do you think the reply TTL from h3 to h1 will be and the winning prefix and action for 10.0.3.3, 10.0.3.99 and 10.0.9.99 based on 1-routing/s1-runtime.json? Give your reasons. After step 6, add the evidence you compare them with your make check output. Identify the winning entry for each probe. Why would working pings with only /32 host routes not establish longest-prefix matching?
The reply TTL from h3 to h1 will be 62, as TTL usually starts at 64 and is decreased by one each router gone through.
The winning prefix will likely be 32 as that's the most common in 1-routing/s1-runtime.json
and the winning action forwarding for the same reason.

### 3. Trace the outgoing Ethernet and IPv4 headers at s1. Which fields change and which stay unchanged? Why must the IPv4 header checksum be recomputed, and why is that a different job from Ethernet's CRC?

### 4. Where does the data plane decide what happens when no destination entry matches. In your program, or in the table's default action? Transfer that reasoning to a table with 192.0.2.0/24 forwarding and 192.0.2.64/26 dropping. What happens to 192.0.2.70, and why? This prefix example is written reasoning, not another network experiment.