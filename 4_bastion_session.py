import time
import subprocess
import socket
import random
import logging
import sys
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) #Turn this on if you're trying to debug the script.

try: 
    import oci
    logging.info("OCI module import is succuessful")
except ImportError: 
    logging.error("Failed to import OCI SDK. Make sure it is installed and accessible.")
    logging.error("Make sure you have followed the OCI SDK installation for your OS located here.")
    logging.error("https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/climanualinst.htm")
    raise SystemExit

timer=(time.time())
###Required Variables###
config = oci.config.from_file(
	"~/.oci/config",
	"DEFAULT") #OCI Configuration File that was generated from the API Key in the OCI CLI
pub_key_file=r"/Users/Jake/.ssh/id_rsa.pub" #Specify the full path of your SSH public key.
#seed_int="358" #You will be given a value to copy here after the first run of the script.
#bastion_host_ocid="ocid1.XX." #OCID of the Bastion Host that was created in OCI
##########################
    
###Optional Variables###
#Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping.
#local_connections=[  
#                    ("10.0.0.254", 8000),
#                    ("10.0.1.130", 3389),
#                    ("10.0.0.3", 21),
#                    ("10.0.0.254", 22)
#                    ] 
session_ttl=1800 #60 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.
session_display_name="MadeWithPython"
##########################

###Predefined Variables###
identity = oci.identity.IdentityClient(config) #Get User Info
bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI
##########################

def port_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        port_open = s.connect_ex((ip, int(port))) == 0
        if port_open:
            s.shutdown(socket.SHUT_RDWR)
    except Exception:
        port_open = False
    s.close()
    return port_open
def preflight_checks():
    try:
        global pub_key_contents
        pub_key_open=open(pub_key_file, 'r')
        pub_key_contents=pub_key_open.read()
        logging.info("Pub Key Avail")
    except NameError:
        print("The 'pub_key_file' variable needs to be set before this script can run.")
        print("Make sure keypair is generated and accessible so this script can continue.")
        print("If you don't have a key-pair, running the command 'ssh-keygen' in your shell create a keypair you can use for this configuration.")
        raise SystemExit
    try:
        seed_int
        if seed_int != "":
            random.seed(seed_int)
            logging.info("Seed Set")
    except NameError:
        seedling=random.randint(1,10000)
        print("Update the seed_int variable with the value below before continuing.")
        print("seed_int="+str(random.randint(1,10000)))
        print("")
        raise SystemExit
    try:
        print("Authenticating OCI User...")
        auth_status=(identity.get_user(config["user"]).data.lifecycle_state)
        if auth_status == "ACTIVE":
            print("OCI User Has Been Authenticated...")
    except NameError:
        print("The OCI Console can help create a configuration file for your user.")
        print("---------->Profile->'Username'->API Key")
        print("1.) Create an API key")
        print("2.) Download the private key and add it you your .oci directory")
        print("3.) Copy the config file to your .oci directory") 
        raise SystemExit
    try:
        if bastion_host_ocid != "":
            logging.info("Bastion Host ID is set")
    except NameError:
        print("The Bastion OCID needs to be set at the beginning of the Python Script.")
        print("Update the bastion_host_ocid with the Bastion Host OCID you want to connect to")
        raise SystemExit
    try:
        subprocess.call(["ssh"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.STDOUT)
        logging.info("SSH is available")
    except Exception:
        print("OpenSSH needs to be accessible to use this script")
        print("If you are using Windows, make sure you are using 64 Bit Python and that OpenSSH is installed on your machine")
        print("You should be able to run 'ssh' in powershell and get a response from the shell.")
        print("Exiting ... ")
        raise SystemExit
    try:
        port_open(bastion_fqdn, 22)
        print("Bastion Host {} is Reachable".format(config["region"]))
        print("")
    except NameError:
        print("Unable to reach the bastion host "+bastion_fqdn)
        raise SystemExit
try:
    preflight_checks()
except Exception:
    raise SystemExit
def local_port_generator():
        port_value=random.randint(20000,50000)
        return(port_value)
def bastion_session_timeout():
        #print(timer-time.time()) #Time the sessions
        print("")
        print("End the session with 'CNTL-C' (Mac/Linux) or 'CNTL-z'+'enter' (Windows)")
        print("Ending this session will close the Bastion Session and Destroy the Forwarding Sessions.")
        while True:
            try:
                time.sleep(1)
                session_status = bastion_client.get_session(session_id=bastion_session.data.id)
                if session_status.data.lifecycle_state != "ACTIVE":
                    print("")
                    print("Bastion Session Expired.")
                    print("Run the script again to continue.")
                    print("The current session TTL is {} minutes".format(session_ttl/60))
                    raise SystemExit
                    quit(-1)
            except:
                try:
                    bastion_client.delete_session(session_id=bastion_session.data.id)
                    print("")
                    print("Session has been cleaned up.")
                except:
                    break
                quit(-1)
def create_bastion_session():
    print("OCI Is Creating A Bastion Session...")
    global bastion_session
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
        timeout = time.time()+10
        while timeout>time.time():
            try:
                subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)),
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.STDOUT)
                time.sleep(.1)
                if port_open("127.0.0.1", local_port) == True:
                    print("{}:{} <--MAPPED TO--> localhost:{}".format(ip_addr, remote_port, local_port))
                    break
                else:
                    time.sleep(.1)
                    #print(port_open("127.0.0.1", local_port))
                    continue
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
        print("Local forwarding is possible by uncommenting the 'local_connections' variable in the Python script.")
        print("This will provide a scalable and re-usable 1:1 mappings for non-SOCKS applications.")
    bastion_session_timeout()
script_navigator()


#TODO
#Script works well. Next step would be to replace use the asyncio module to run muliple SSH instances and watch each process. 
#This would let me restart the process when it fails (while the bastion session is up) or close the script on failure
#I would also get better error handling instead of waiting for the port to listen on the local machine.

#Could list the bastion hosts that are available to the user if they havne't set an OCID.

#Stretch goal
#Figure out how to make asyncio a fake VPN, avoiding local forwarding configuration and 1:1 mapping
