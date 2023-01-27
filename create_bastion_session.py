import oci
import time
import subprocess


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
##########################

###Optional Variables###
#local_connections - Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping
#debug_SSH_tunnel_mode #add a variable to add the -v option. 
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

def verify_user_authed():
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

def connect_socks5():
    try:
        print("\n\n\n##########LEAVE THIS WINDOW OPEN##########")
        print("Point your SOCKS5 client [Web Browser], [DB Client], [etc] to . . .")
        print("------------------>localhost:5000<------------------\n")
        print("Application that are not SOCKS aware [RDP] can still take advantage of local forwarding.\nGo to the README for more info.")
        print("##########LEAVE THIS WINDOW OPEN##########")
        subprocess.run(("ssh", "-o serveraliveinterval=60", "-N", "-D", "127.0.0.1:5000", "{}@{}".format(bastion_session.data.id, bastion_fqdn, "-o serveraliveinterval=60")))
    except:
        print("Session Has Ended. Run the Script Again to Open A New Session")
        quit(-1)

def connect_local():
    print("You can set this as a dictionary of values if you plan on connecting to these instances frequently\n just uncomment and add your data to the sample variable XXX\n\n")
    try: 
        local_connections
        print("Connections already exist, adding them to the ")
        #Use a loop and interate through the dictionary
    except:
        print("Here are some inputs you need to make a 1:1 mapping with your OCI instances\n")
        print("The Connection Goes This Way\n")
        print("Localmachine(Localport)--->OCI_Instance(Serving_Port)\n")
        oci_private_ip=input("IP of the Instance You want to connect to\n")
        remote_port=input("OCI Port you want to connect to\n")
        local_port=input("Port you are going to connect to on your local machine to forward this connection.\n Usually a unique number >1024 is needed here\n")
        print("Connecting to " + oci_private_ip + " on port " + remote_port)
        subprocess.Popen(("ssh", "-o serveraliveinterval=60", "-N", "-L",  "{}:{}:{}".format(local_port, oci_private_ip, remote_port), "{}@{}".format(bastion_session.data.id, bastion_fqdn)))
        print("Connected\n Connect to your OCI instance using a client with localhost:" +local_port) 

def verify_session_active():
    session_response=bastion_client.get_session(session_id=bastion_session.data.id)
    if session_response.data.lifecycle_state == "ACTIVE":
        print("Creating a Local Tunnel through the Bastion Session\n")
        time.sleep(5)
        connect_socks5()
    if session_response.data.lifecycle_state == "CREATING":
        print("OCI Is Creating The Bastion Session . . .")
        session_response=bastion_client.get_session(session_id=bastion_session.data.id)
        time.sleep(2)
        verify_session_active()
    if session_response.data.lifecycle_state == "DELETED":
        print("The Bastion Session has Timed Out.\n Run the Script Again to Create a New One")
        quit(-1)
        #create_bastion_session()
        #Might be able to loop through and create an additional session

verify_session_active()


#Error handling needed for ssh client
#Error #1
#Connection closed by 147.154.11.76 port 22
#Sometimes a connection is not able to be completed and the script closes. I need to build in a "retry" if I get this error instead of failing the script.
#
#Error #2
#Connection to host.bastion.us-ashburn-1.oci.oraclecloud.com closed by remote host.
#The session closes after 30 minutes (usually). If I want to create a new session, I should just have to press "ENTER" and it will rebuild my session, or CNTL-C to exit.
#
#Error #3
#If the Python Script exits (CNTL-C), need to gracefully kill the ssh session before exit so there isn't a stale SSH session. (Eventually it will close, but this would make the script better)
