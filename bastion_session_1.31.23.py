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
pub_key_file="/Users/Jake/.ssh/id_rsa.pub"
seed_int=9756 #You will be given a value to copy here after the first run of the script.
##########################

###Optional Variables###

#Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping.
local_connections=[
        ("10.0.0.1", 3389),
        ("10.0.0.2", 1521),
        ("10.0.0.3", 21)
        ] 
session_ttl=1800 #30 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.
session_display_name="MadeWithPython"
##########################

###Predefined Variables###
identity = oci.identity.IdentityClient(config) #Get User Info
bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI
pub_key_open=open(pub_key_file, 'r')
pub_key_contents=pub_key_open.read()

##########################

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
    print("\nAuthenticating User. . .")
    auth_status=(identity.get_user(config["user"]).data.lifecycle_state)
    if auth_status == "ACTIVE":
        print("User Has Been Authenticated With OCI\n")
    else:
        print("Unable to Authenticate. . . Make sure you have the OCI cli installed and the user configured")
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
        print("Exiting . . . ")
        quit(-1)

verify_ssh_avail()

def verify_bastion_host_avail():
    try:
        port_open(bastion_fqdn, 22)
        print("Connected to Bastion Host in "+config["region"])
    except:
        print("Unable to reach the bastion host "+bastion_fqdn)
        quit(-1)

def local_random():
        
        port_value=random.randint(20000,50000)
        return(port_value)
        #Define a local port. This avoids local port collisions which cause Bastions sessions to terminate prematurely.

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
    print("You can set this as a dictionary of values if you plan on connecting to these instances frequently\n just uncomment and add your data to the sample variable XXX\n\n")
    #local_port=local_random()
    try: 
        if local_connections != "":
            print("Opening Predefined Connections")
            for (ip_addr, remote_port) in local_connections:
                local_port=local_random()
                subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)))
                print("Connections from localhost:{} MAPPED TO {}:{}".format(local_port, ip_addr, remote_port))
            holding_pattern=input("\nPress Control-C to close the local forwarding Session:\n")
        else:
            local_port=local_random()
            print("Here are the inputs you need to make a 1:1 mapping with your OCI instances")
            print("localmachine(Localport)--->OCI_Instance(Serving_Port)\n")
            oci_private_ip=input("Private IP of the OCI Instance You want to connect to\n>")
            remote_port=input("\nOCI Port you want to connect to\n>")
            print(local_port)
            #print("Connecting to " + oci_private_ip + " on port " + remote_port)
            #print("\n\n\nConnected!\nConnect to your OCI instance through \nlocalhost:" +local_port) 
            local_forwarding=subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, oci_private_ip, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)))
            #Error handling from sdrerr, if port is unavailable, like the below error.
            #SSH Error Line#1 :channel_setup_fwd_listener_tcpip: cannot listen to port: 10001
            #SSH Error Line#2 : Could not request local forwarding.
            holding_pattern=input("\nPress Control-C to close the local forwarding Session:\n")
    except:
        print("Rerun the script to create a new session.")
        quit(-1)
        
def socks5_session():
    timeout = time.time()+11
    socks5_lport=local_random()
    while timeout>time.time():
        print("\nThe Bastion Session is Active. Establishing the Tunnel. . .")
        try:
            socks5_subprocess=subprocess.Popen((("ssh", "-o serveraliveinterval=60", "-N", "-D", "{}:{}".format("127.0.0.1",socks5_lport), "{}@{}".format(bastion_session.data.id, bastion_fqdn, 
            stdout=None, 
            stderr=None,
            capture_output=False))))
            time.sleep(2)
            if port_open("127.0.0.1", socks5_lport):
                print("\n\n\n!!!!!Tunnel Established!!!!!\n")
                print("########################################LEAVE THIS WINDOW OPEN##############################")
                print("##               Point your SOCKS5 client [Web Browser], [DB Client], [etc] to . . .")
                print("                                localhost:" +str(socks5_lport))
                print("##")
                print("## Applications that are not SOCKS aware [RDP] can still take advantage of local forwarding.")
                print("## Set the ''local_connections' variable to statically build many local forwarding sessions.")
                print("#############################################################################################")
                while True:
                    #Evenually add "If local_connections var is set, run the function. Otherwise, wait for the user to do it."
                    moreconnections=input("\nType 'local' to configure local forwarding sessions. Press 'Control-C' to tear down the SOCKS5 session.\nNOTE:SOCKS5 and Local forwarding will run at the same time over the Bastion Session.\n>")
                    if moreconnections != "local":
                        continue
                    else:
                        connect_local()

        except:
            socks5_subprocess.kill()
            bastion_client.delete_session(session_id=bastion_session.data.id)
            print("\nConnection Closed. Run the script to build another session!")

def verify_bastion_session_lifecycle():
    session_response=bastion_client.get_session(session_id=bastion_session.data.id)
    if session_response.data.lifecycle_state == "ACTIVE":
        socks5_session()
    if session_response.data.lifecycle_state == "CREATING":
        print("OCI Is Creating The Bastion Session . . .")
        session_response=bastion_client.get_session(session_id=bastion_session.data.id)
        time.sleep(1)
        verify_bastion_session_lifecycle()
    if session_response.data.lifecycle_state == "DELETED":
        print("The Bastion Session has Timed Out.\n Run the Script Again to Create a New One")
        quit(-1)

verify_bastion_session_lifecycle()

###TODO###
##Need to test on a Windows Client, and then redo the whole script :)
