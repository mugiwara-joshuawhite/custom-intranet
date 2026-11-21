# Custom Intranet, part 2: switching and a tunnel Group JD Writeup

## Tasks, and member who did them
Tasks:
- Q1 []
- switching.MyIngress.forward() []
- switching.MyIngress.flood() []
- switching.MyIngress.apply []
- switching.MyEgress.apply []
- Q2 []
- Q3 []
- Q4 []
- Q5 []
- tunnel.MyParser.parse_ipv4() []
- tunnel.MyEgress.encap() [Both]
- tunnel.MyEgress.decap() []
- Q6 []
- Q7 []
- Q8 []

## Questions and Answers

### 1. h1 sends an ARP request for h3's address, and h3 replies. For each of the two frames, predict which ports it leaves the switch by, and which entries the controller writes after it.

### 2. Which ports carried the ARP request, and which carried the reply? Name the packet numbers and files. Compare with your prediction in answer 1, and explain each difference or why the prediction held. Which line of the controller's log made the reply go to one port only?

### 3. Is it the same? Compare the bridge's captures with your switch's: are the same frames on the same ports? Then name one difference in how the two work, even where the wire looks the same. linux.sh turns two things off; say what they are and why a Linux bridge sends packets your P4 switch never does. 

### 4. Name one situation where this switch would not work as expected, and explain why.

### 5. A sends a ping to B with TTL 64. If the packet that leaves port 1 what are its outer source and destination, its protocol number, its inner source and destination, and both TTLs. How many bytes longer it is than the packet A sent, and the largest inner packet that fits through a 1500-byte link. Compare this to what you get after you run the code.

### 6. For one packet into the tunnel and one out of it, give the outer and inner source and destination and both TTLs, with packet numbers. Compare them with answer 5, and explain each difference or why the prediction held. Which bytes did the tunnel add, and where in the packet are they?

### 7. Is it the same, byte for byte? Compare the outer IPv4 header of one tunnel packet from each capture, field by field. Name every field that differs, and explain why the difference does not change where the packet goes or whether it arrives.

### 8. Name one situation where this tunnel would not work as expected, and explain why.