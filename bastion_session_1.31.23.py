import oci
import time
import subprocess
import socket
import random


###Required Variables###
#OCID of the Bastion Host that was created in OCI
bastion_host_ocid="ocid1.bastion.oc1.iad.amaaaaaac3adhhqa5z4bkw5hvtwu7cyf4bqgprl665qjwyrnteucyx2f46cq"
#OCI Configuration File that was generated from the Python SDK
config = oci.config.from_file(
	"~/.oci/config",
	"DEFAULT")
#Specify the full path of your SSH public key. The Bastion Host Requires the public key in RSA format.
#The Bastion Host and your client SSH session will use the same keys in this configuration. The OCI profile keys are used to authenticate the user.
pub_key_file=r"/Users/Jake/.ssh/id_rsa.pub"
seed_int=9756 #You will be given a value to copy here after the first run of the script.
##########################

###Optional Variables###

#Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping.
local_connections=""
#local_connections=[  
#                    ("10.0.0.254", 8000),
#                    ("10.0.1.130", 3389),
#                    ("10.0.0.3", 21)
#                    ] 
session_ttl=1800 #60 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.
session_display_name="MadeWithPython"
##########################

###Predefined Variables###
identity = oci.identity.IdentityClient(config) #Get User Info
bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI
pub_key_open=open(pub_key_file, 'r')
pub_key_contents=pub_key_open.read()

##########################

def port_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        port_open = s.connect_ex((ip, int(port))) == 0 # True if open, False if not
        if port_open:
            s.shutdown(socket.SHUT_RDWR)
    except Exception:
        port_open = False
    s.close()
    return port_open
    
def ssh_rsa_set():
    if pub_key_contents:
        return
    else:
        print("The 'pub_key_file' variable needs to be set before this script can run.")
        print("Make sure keypair is generated and accessible so this script can continue.")
        print("If you don't have a key-pair, running the command 'ssh-keygen' in your shell create a keypair you can use for this configuration.")
        quit(-1)

ssh_rsa_set()

def pseudo_random_ports():
    if seed_int != "":
        random.seed(seed_int)
        return
    else:
        print("Update the static_local_ports variable with the value below before continuing.")
        seedling=random.randint(1,10000)
        print("seed_int="+str(random.randint(1,10000)))
        quit(-1)

pseudo_random_ports()

def verify_user_authed():
    print("")
    print("Authenticating OCI User...")
    auth_status=(identity.get_user(config["user"]).data.lifecycle_state)
    if auth_status == "ACTIVE":
        print("OCI User Has Been Authenticated...")
    else:
        print("Unable to Authenticate... Make sure you have the OCI cli installed and the user configured")
        print("Install OCI CLI Python SDK - https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/climanualinst.htm")
        print("The OCI Console can help create a configuration file for your user.")
        print("---------->Go to Profile->'Username'->API Key")
        print("When creating an API key, you can upload your current public key and convert it to PEM with this command.")
        print("'ssh-keygen -f id_rsa.pub -e -m pem' where 'id_rsa.pub' is your public key")
        quit(-1)

verify_user_authed()  

def verify_bastionocid_set():
    if bastion_host_ocid == "":
        print("The Bastion OCID needs to be set at the beginning of the Python Script.")
        print("Update the bastion_host_ocid with the Bastion Host OCID you want to connect to")
        quit(-1)

verify_bastionocid_set()

def verify_ssh_avail():
    try:
        subprocess.call(["ssh"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.STDOUT)
    except:
        print("OpenSSH needs to be accessible to use this script")
        print("If you are using Windows, make sure you are using 64 Bit Python and that OpenSSH is installed on your machine, and is assessable by 'ssh'")
        print("Exiting ... ")
        quit(-1)

verify_ssh_avail()

def verify_bastion_host_avail():
    try:
        port_open(bastion_fqdn, 22)
        print("Bastion Host {} is Reachable".format(config["region"]))
        print("")
    except:
        print("Unable to reach the bastion host "+bastion_fqdn)
        quit(-1)

verify_bastion_host_avail()

def local_random():
        
        port_value=random.randint(20000,50000)
        return(port_value)
        #Define a local port. This avoids local port collisions which cause Bastions sessions to terminate prematurely.

def create_bastion_session():
    try:
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
    except:
        print("Unable to create a new Bastion Session. Unknown Error")
        quit(-1)

create_bastion_session()

def connect_local():
    try: 
        if local_connections != "":
            print("")
            print(">>>1:1 OCI Instance Mappings<<<")
            for (ip_addr, remote_port) in local_connections:
                local_port=local_random()
                try:
                    time.sleep(.2)
                    subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)))
                except:
                    print("Unable to connect to {}:{}".format(ip_addr, remote_port))
                print("{}:{} MAPPED TO localhost:{}".format(ip_addr, remote_port, local_port))
            print("")
            print("Press Control-C to close the terminal")
            while True:
                holding_pattern=input(">")
                if holding_pattern == "":
                    continue              
                else:
                    KeyboardInterrupt
                    pass
        else:
            local_port=local_random()
            print("Here are the inputs you need to make a 1:1 mapping with your OCI instances")
            print("localmachine(Localport)--->OCI_Instance(Serving_Port)\n")
            print("Private IP of the OCI Instance You want to connect to:")
            oci_private_ip=input(">")
            print("OCI Port you want to connect to:")
            remote_port=input(">")
            print(local_port)
            print("Connect to your OCI instance through:")
            print("localhost:{}".format(local_port)) 
            local_forwarding=subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, oci_private_ip, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)))
            #Error handling from sdrerr, if port is unavailable, like the below error.
            #SSH Error Line#1 :channel_setup_fwd_listener_tcpip: cannot listen to port: 10001
            #SSH Error Line#2 : Could not request local forwarding.
            print("Press Control-C to Exit")
            while True:
                holding_pattern=input(">")
                if holding_pattern == "":
                    continue              
                else:
                    KeyboardInterrupt
                    pass
    except:
        print("")
        print("Run the script again to continue your session.")
        quit(-1)
        
def socks5_session():
    timeout = time.time()+11
    socks5_lport=local_random()
    print("\nThe Bastion Session is Active. Establishing the Tunnel...")
    time.sleep(3)
    while timeout>time.time():
        try:
            socks5_subprocess=subprocess.Popen(["ssh", "-o serveraliveinterval=60", "-N", "-D", "{}:{}".format("127.0.0.1",socks5_lport), "{}@{}".format(bastion_session.data.id, bastion_fqdn)],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.STDOUT)
            time.sleep(2)
            if port_open("127.0.0.1", socks5_lport):
                print("Connection Established Over the Bastion Session!")
                print("")
                print("#####LEAVE THIS WINDOW OPEN#####")
                print(">>>SOCKS5 PROXY<<<")
                print("MAPPED TO localhost:{}".format(socks5_lport))
                if local_connections != "":
                    time.sleep(2) #Might need a little more time to create the 1:1s
                    connect_local() 
                else:
                    while True:
                        print("")
                        print("Type 'local' to configure local forwarding to an OCI instance.")
                        print("You can set the 'local_connections' variable to do this automatically")
                        print("")
                        print("Press 'Control-C' (Mac/Linux) or 'Control-z'+'enter' (Windows) to destroy the session.")
                        moreconnections=input(">")
                        if moreconnections != "local":
                            print("Notavalidentry")
                            continue
                        else:
                            connect_local()
            else:
                continue
        
        except:
            bastion_client.delete_session(session_id=bastion_session.data.id)
            print("")
            print("Bastion Session is Deleted and Script is Closed.")
            quit(-1)

def verify_bastion_session_lifecycle():
    session_response=bastion_client.get_session(session_id=bastion_session.data.id)
    if session_response.data.lifecycle_state == "ACTIVE":
        socks5_session()
    if session_response.data.lifecycle_state == "CREATING":
        print("OCI Is Creating A Bastion Session...")
        session_response=bastion_client.get_session(session_id=bastion_session.data.id)
        time.sleep(3)
        verify_bastion_session_lifecycle()
    if session_response.data.lifecycle_state == "DELETED":
        print("The Bastion Session has Timed Out.\n Run the Script Again to Create a New One")
        quit(-1)

verify_bastion_session_lifecycle()

###TODO###
##Need to test on a Windows Client, and then redo the whole script :)
#Initial Testing Shows that this is working.
#
#Need Popen to be aware of the (-1) status code of the process and close the script.
#Connection to host.bastion.us-ashburn-1.oci.oraclecloud.com closed by remote host.
#Transferred: sent 3904, received 2084 bytes, in 1799.7 seconds
#Bytes per second: sent 2.2, received 1.2
#debug1: Exit status -1
#I tried to increase the timeout on the bastion session to see if it's bastions fault or an SSH config issue.
#
#Timeout definitely happens with 30min of inactivity on the proxy.
#Transferred: sent 6780, received 5420 bytes, in 1866.5 seconds
#Bytes per second: sent 3.6, received 2.9
#debug1: Exit status -1
#Connection to host.bastion.us-ashburn-1.oci.oraclecloud.com closed by remote host.
#
#Also need to do some error handling for a closed bastion session
#raise exceptions.ServiceError(
#oci.exceptions.ServiceError: {'target_service': 'bastion', 'status': 409, 'code': 'Conflict', 'opc-request-id': 'B38F43853FB849C296339CC5841C1BBA/ACBF59C7D67860E5770F653CF4AE835E/21531FACE093480CC0023E8432E4B764', 'message': 'resource is not allowed to delete with current state', 'operation_name': 'delete_session', 'timestamp': '2023-01-31T21:02:01.794542+00:00', 'client_version': 'Oracle-PythonSDK/2.90.2', 'request_endpoint': 'DELETE https://bastion.us-ashburn-1.oci.oraclecloud.com/20210331/sessions/ocid1.bastionsession.oc1.iad.amaaaaaac3adhhqa2eley4ow7ww5x3hmcvrtgbl5rm4mtx4dl5aqxsquce7q', 'logging_tips': 'To get more info on the failing request, refer to https://docs.oracle.com/en-us/iaas/tools/python/latest/logging.html for ways to log the request/response details.', 'troubleshooting_tips': "See https://docs.oracle.com/iaas/Content/API/References/apierrors.htm#apierrors_409__409_conflict for more information about resolving this error. Also see https://docs.oracle.com/iaas/api/#/en/bastion/20210331/Session/DeleteSession for details on this operation's requirements. If you are unable to resolve this bastion issue, please contact Oracle support and provide them this full error message."}

#Local Sessions Closing Prematurly. Need to use the port_open function to retry the mapping if it's unsuccuessful.
#10.0.0.254:8000 MAPPED TO localhost:34003
#10.0.1.130:3389 MAPPED TO localhost:35849
#Connection closed by 147.154.11.76 port 22
#10.0.0.3:21 MAPPED TO localhost:21990

#Press Control-C to close the terminal
#:Connection closed by 147.154.11.76 port 22
