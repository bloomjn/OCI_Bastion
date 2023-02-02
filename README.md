# OCI_Bastion

	• Cross Platform
	• Setup is simple, One variable is need to create a session (Bastion Host OCID)
	• Reuses existing session if session is active but SSH session has terminated
	• Easy SOCKS5 Proxy
	• For Non-SOCKS5 aware traffic, easy traffic forwarding
	• Traffic forwarding using native OS tools (OpenSSH). No complex PySocks, Paramiko, etc configs. 
	• OpenSSH has a reputation for being stable and is on every major OS, even Windows. 
	• Secure all of your traffic to OCI over the internet, regardless if it’s encrypted by the application. 
	• Completely avoid public access to OCI resources instead using Bastion as a jump host. 
	• No need to build/pay for a jump host when you can “have your laptop sitting in an Oracle Region”
	• As an administrator, you can grant a user “create session” access. Revoked access is immediately pulled. 
	• DNS traffic can be tunneled over SOCKS5 (need to see if I can proxy DNS traffic over local forwarding)
	• The SSH configuration profile times out SSH sessions after 5 minutes. This avoids that, and uses the session TTL for session closure.
	• Encrypts DNS requests over the internet without DNSSEC
	• No need to manipulate the SSH config file to connect to your bastion host
	• One SOCKS5 session can do all of the local forwarding and proxying, significantly increasing the scale of the Bastion host session count. 
	• Possible to forward traffic over a FastConnect, encrypted, and access OSN services once you are in the Bastion? At least connect to the private IP of the bastion over the FC and tunnel traffic. 
	• Does enabling a SOCKS5 proxy allow for DNS tunneling automatically if a systemwide config is used? --Must use SOCKS5
    Localforwarding configuration allows for IPv6 connections over ::1:localport
