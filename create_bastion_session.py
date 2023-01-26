import oci
import time
import subprocess


###Required Variables###
bastion_host_ocid="ocid1.bastion.oc1.iad.amaaaaaac3adhhqa5z4bkw5hvtwu7cyf4bqgprl665qjwyrnteucyx2f46cq"

#OCI Configuration File
config = oci.config.from_file(
	"~/.oci/config",
	"DEFAULT")

#The Bastion Host Requires the public key in RSA format. I used the ssh-keygen utility to create mine (MacOS).
#ssh-keygen -y -f ~/.ssh/id_rsa. Example "ssh-rsa LOTSOFSTUFF". Make sure it copies with no line breaks.
sshrsa=("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC36lRHA/HZbFBjfYdDWAKlg6ebpkmXvvLmogDLjcl54EKX3S658NsyaAWprZ7/OWNFR0G00nsr+QvGkrzSz0NIneA1UnOaPlyfmcib868N6sSL3QNfHONrnohW++PM9q0q/lG17hpVSJifLJahhZsKOgHfrE6MA5shwdUA0T11d1s8OF6dXBjUjT+MFbrasLz9eU34iLQjJaSnPnE/OEnUCREaFo4fQeFGWAkNQAEj6qlh2+cIZl3UamLiUmOqFs8pF2W06wgfi0wZO20g3JQWr8NgBoBu+KsUg3VbHdHzExS2CKYzxeXb0xdVqwCRW80JJDVIAlcZIPGFGqSXAnFEKisYTJc4QajQJ9N+TOQwuGzQMS3pLHyfdtY9FQOrI9sDuSH+J0VZE86+eXMCYAIHRwByqomwNyzJdkIVsby1fBDJSRv4P5rZaeV2i9PJOakW0VDVjUjO29gUmtxl+Gg1Vv/5DhMJdBXdtpd1EiAbD1PWXw8osjMZnpD2H1PK/JE= jake@jake-mac")

###Optional Variables###
#local_connections - Create a sample list of instances to connect to if looking for a nonSOCKS aware app or 1:1 instance mapping
#debug_SSH_tunnel_mode #add a variable to add the -v option. 
session_ttl=1800 #30 Minutes by default, and gives a good 
session_display_name="MadeWithPython"

###Predefined Variables###
identity = oci.identity.IdentityClient(config) #Get User Info
bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI

def ssh_rsa_set():
    if sshrsa!="":
        return
    else:
        print("The sshrsa variable needs a to be set before the script can create a Bastion Session")
        quit(-1)
ssh_rsa_set()

def verify_user_authed():
    auth_status=(identity.get_user(config["user"]).data.lifecycle_state)
    if auth_status == "ACTIVE":
        print("User Has Been Authenticated\n")
    else:
        print("Make sure to follow the pre-requesits to the script before continuing. Your user isn't authenticated")
        quit(-1)

verify_user_authed()  

def verify_bastionocid_set():
    if bastion_host_ocid == "":
        print("The Bastion OCID needs to be set at the beginning of the Python Script. Edit the script before continuting.")
        quit(-1)

verify_bastionocid_set()

def verify_ssh_avail():
    try:
        subprocess.call(["ssh"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.STDOUT)
    except:
        print("OpenSSH needs to be accessible to use this script")
        print("If you are using Windows, make sure you are using 64 Bit Python")
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
                        public_key_content=sshrsa),
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
