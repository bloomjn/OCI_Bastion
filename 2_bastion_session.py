try: 
    import oci
except Exception: 
    print("Make sure you have followed the OCI SDK installation for your OS located here.")
    print("https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/climanualinst.htm")

import time
import subprocess
import socket
import random

###Required Variables###
bastion_host_ocid="ocid1.bastion.oc1.iad.amaaaaaac3adhhqa5z4bkw5hvtwu7cyf4bqgprl665qjwyrnteucyx2f46cq" #OCID of the Bastion Host that was created in OCI
config = oci.config.from_file(
	"~/.oci/config",
	"DEFAULT") #OCI Configuration File that was generated from the Python SDK
#Specify the full path of your SSH public key.
pub_key_file=r"/Users/Jake/.ssh/id_rsa.pub"
seed_int=787 #You will be given a value to copy here after the first run of the script.
##########################

###Optional Variables###
#Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping.
local_connections=[  
                    ("10.0.0.254", 8000),
                    ("10.0.1.130", 3389),
                    ("10.0.0.3", 21)
                    ] 
session_ttl=1800 #60 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.
session_display_name="MadeWithPython"
##########################

###Predefined Variables###
identity = oci.identity.IdentityClient(config) #Get User Info
bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI
pub_key_open=open(pub_key_file, 'r')
pub_key_contents=pub_key_open.read()
random.seed(seed_int)
##########################

def port_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    time.sleep(1)
    try:
        port_open = s.connect_ex((ip, int(port))) == 0
        if port_open:
            s.shutdown(socket.SHUT_RDWR)
    except Exception:
        port_open = False
    s.close()
    return port_open
def local_port_generator():
        port_value=random.randint(20000,50000)
        return(port_value)
#Need to go over preflight_checks again after function merge
def preflight_checks():
    try:
        pub_key_contents
    except:
        print("The 'pub_key_file' variable needs to be set before this script can run.")
        print("Make sure keypair is generated and accessible so this script can continue.")
        print("If you don't have a key-pair, running the command 'ssh-keygen' in your shell create a keypair you can use for this configuration.")
    try:
        seed_int
    except:
        print("Update the static_local_ports variable with the value below before continuing.")
        seedling=random.randint(1,10000)
        print("seed_int="+str(random.randint(1,10000)))
        print("")
    try:
        print("Authenticating OCI User...")
        auth_status=(identity.get_user(config["user"]).data.lifecycle_state)
        if auth_status == "ACTIVE":
            print("OCI User Has Been Authenticated...")
    except:
        print("The OCI Console can help create a configuration file for your user.")
        print("---------->Profile->'Username'->API Key")
        print("1.) Create an API key")
        print("2.) Download the private key and add it you your .oci directory")
        print("3.) Copy the config file to your .oci directory") 
    try:
        bastion_host_ocid
    except:
        print("The Bastion OCID needs to be set at the beginning of the Python Script.")
        print("Update the bastion_host_ocid with the Bastion Host OCID you want to connect to")
    try:
        subprocess.call(["ssh"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.STDOUT)
    except:
        print("OpenSSH needs to be accessible to use this script")
        print("If you are using Windows, make sure you are using 64 Bit Python and that OpenSSH is installed on your machine, and is assessable by 'ssh'")
        print("Exiting ... ")
    try:
        port_open(bastion_fqdn, 22)
        print("Bastion Host {} is Reachable".format(config["region"]))
        print("")
    except:
        print("Unable to reach the bastion host "+bastion_fqdn)
preflight_checks()
def parking_lot():
    while True:
        print("")
        print("End the session with 'CNTL-C' (Mac/Linux) or 'CNTL-z'+'enter' (Windows)")
        try:
            holding_pattern=input(">")
            if holding_pattern=="local":
                    print("Set The Private IP of the OCI Instance You want to connect to:")
                    oci_private_ip=input(">")
                    print("OCI Port you want to connect to:")
                    remote_port=input(">")
                    localforward_tunnel(oci_private_ip,remote_port)
            else:
                continue
        except:
            try:
                bastion_client.delete_session(session_id=bastion_session.data.id)
            except:
                print("There is no bastion session to delete.")
            print("")
            print("Bastion Session is Deleted and Script is Closed.")
            quit(-1)
def create_bastion_session():
    print("OCI Is Creating A Bastion Session...")
    global bastion_session
    global bastion_session_lifecycle_state
    bastion_session=bastion_client.create_session(
            create_session_details=oci.bastion.models.CreateSessionDetails(
                bastion_id=bastion_host_ocid,
                target_resource_details=oci.bastion.models.CreateManagedSshSessionTargetResourceDetails(
                    session_type="DYNAMIC_PORT_FORWARDING"),
                    key_details=oci.bastion.models.PublicKeyDetails(
                    public_key_content=pub_key_contents),
                display_name=session_display_name,
                key_type="PUB",
                session_ttl_in_seconds=session_ttl))
    bastion_session_id=bastion_session.data.id
    bastion_session_lifecycle_state=bastion_session.data.lifecycle_state
    print("Bastion Session is being Created.")
    print("This Will Take A Few Moments.")
    while True:
        session_response=bastion_client.get_session(session_id=bastion_session.data.id)
        if session_response.data.lifecycle_state == "CREATING":
            continue
        else:
            break
create_bastion_session()
def socks5_tunnel():
    local_port=local_port_generator()
    timeout = time.time()+10 #Built in failsafe
    while timeout>time.time():
        try:
            subprocess.Popen(["ssh", "-o serveraliveinterval=60", "-N", "-D", "{}:{}".format("127.0.0.1",local_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.STDOUT)
            port_open("127.0.0.1", local_port)
            if port_open("127.0.0.1", local_port) == False:
                continue
            else:
                print("")
                print("SOCKS5 PROXY <--MAPPED TO--> localhost:{}".format(local_port))
                break
        except:
            print("Unable to create a SOCKS5 session")
def localforward_tunnel(ip_addr,remote_port):
        local_port=local_port_generator()
        timeout = time.time()+5
        while timeout>time.time():
            try:
                subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)),
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.STDOUT)
                if port_open("127.0.0.1", local_port) == False:
                    continue
                else:
                    print("{}:{} <--MAPPED TO--> localhost:{}".format(ip_addr, remote_port, local_port))
                    break
            except:
                print("Unable to connect to {}:{}".format(ip_addr, remote_port))
def script_navigator():
    socks5_tunnel()
    try:
        local_connections
        for (ip_addr, remote_port) in local_connections:
            localforward_tunnel(ip_addr,remote_port)
    except:
        print("")
        print("Type 'local' to configure local forwarding to an OCI instance.")
        print("You can set the 'local_connections' variable to do this automatically")
        print("")
    parking_lot()
script_navigator()

#TODO
# Use Popen communicate to get a non(-1) exit code and then continue. 
#	Asyncio might be able to watch for a (-1) exit code indefinitely while I run other processes. 
#	https://queirozf.com/entries/python-3-subprocess-examples

#Error Handling
#	(WIP)“Import OCI” error handling
#	Cntl-C deletes the bastion session, whiule Asyncio/Subprocess manages the SSH session and keeps it active. 
#	(WIP)Consolidate pre-checks into one function.
	
#Speed
#	Should take less than 10 seconds to complete the script. Sometimes the SSH sessions hang and it takes about 15sec
	
#Stretch goal
#Figure out how to make asyncio a fake VPN, avoiding local forwarding configuration and 1:1 mapping
