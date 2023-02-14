###MODULES###
import random
import asyncio
import subprocess
import socket
import logging
import argparse
import sys
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) #Turn this on if you're trying to debug the script.
try: 
    import oci
    logging.info("OCI module import is succuessful")
except ImportError: 
    print("Failed to import OCI SDK. Make sure it is installed and accessible.")
    print("Make sure you have followed the OCI SDK installation for your OS located here.")
    print("https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/climanualinst.htm")
    raise SystemExit
##############
        
###Required Variables###
oci_config_location="~/.oci/config" #OCI Configuration File that was generated from the API Key in the OCI GUI. Change if this is not the default
oci_config_profile="DEFAULT" #If you are using more than one profile in your OCI config, this is where you specify the profile you want to use. Common for multi region deployments
pub_key_file=r"/Users/Jake/.ssh/id_rsa.pub" #Specify the full path of your SSH public key. This is not the same thing as your OCI RSA KEY. This file is most likely named 'id_rsa.pub' in your .ssh folder.
seed_int="5602" #You will be given a value to copy here after the first run of the script.
bastion_host_ocid="ocid1.bastion.oc1.iad.amaaaaaac3adhhqa5z4bkw5hvtwu7cyf4bqgprl665qjwyrnteucyx2f46cq" #OCID of the Bastion Host you want to create sessions with on OCI.

###Optional Variables###
session_ttl=1800 #30 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.

#local_connections=[("10.0.0.254", 8000),("10.0.1.130", 3389),("10.0.0.3", 21),("10.0.0.254", 22)] #Set OCI_PRIVATE_IP and OCI_DEST_PORT for non-SOCKS5 applications to do local forwarding.
##########################

CLI=argparse.ArgumentParser()
CLI.add_argument("--bastion_ocid","-b", type=str)
CLI.add_argument("--random_number", "-r", type=int)
CLI.add_argument("--profile", "-p", type=str)
CLI.add_argument("--session_ttl", "-s", type=int)
CLI.add_argument("--local_connections", "-l", type=str, action="append", nargs="+")
args=CLI.parse_args()

if args.bastion_ocid != None:
    bastion_host_ocid=args.bastion_ocid
if args.random_number != None:
    seed_int=args.random_number
if args.profile != None:
    oci_config_profile=args.profile
if args.session_ttl != None:
    session_ttl=args.session_ttl
if args.local_connections != None:
    local_connections_list=args.local_connections
    local_connections=[tuple(x) for x in local_connections_list]

###SCRIPT###
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
        print("Make sure a SSH keypair is generated and accessible so this script can continue.")
        print("If you don't have a SSH key-pair, running the command 'ssh-keygen' in your shell will create a keypair you can use for this configuration.")
        raise SystemExit
    try:
        global config
        config = oci.config.from_file(oci_config_location, oci_config_profile)
        oci.config.validate_config(config)
        global identity
        identity = oci.identity.IdentityClient(config) #Get User Info
        global bastion_client
        bastion_client = oci.bastion.BastionClient(config) #Interact with Bastions on OCI
    except Exception as e:
        print("There is an error with your OCI config file")
        print("")
        print(oci.config.InvalidConfig(e))
        raise SystemExit
    try:
        seed_int
        random.seed(seed_int)
        logging.info("Seed Set")
    except NameError:
        seedling=str(random.randint(1,10000))
        print("Update the seed_int variable with the value below before continuing.")
        print("seed_int="+seedling)
        print("")
        print("You can add also just add this as a cli parameter")
        print("python3 pythonscriptname.py -r " +seedling)
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
        bastion_host_ocid
        logging.info("Bastion Host ID is set")
    except NameError:
        print("The Bastion OCID needs to be set at the beginning of the Python Script.")
        print("Update the bastion_host_ocid with the Bastion Host OCID you want to connect to")
        raise SystemExit
    try:
        splitter=bastion_host_ocid.split('.')
        bastion_region_code=splitter[3]
        available_regions = identity.list_regions()
        for region in available_regions.data:
            region_key_val=region
            if region_key_val.key == bastion_region_code.upper():
                bastion_region_name=(region_key_val.name)
        if bastion_region_name != config["region"]:
            print("Your user profile is not in the same OCI region as the Bastion you're trying to connect to.")
            print("Make sure you're using the right profile in your OCI config.")
            print("Otherwise, create an API key for this region and add the configuration of your OCI config file.")
            raise Exception
    except NameError:
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
        global bastion_fqdn
        bastion_fqdn = "host.bastion." + config["region"] + ".oci.oraclecloud.com" #OCI SDK does not show the bastion FQDN, so we have to make it manually
        port_open(bastion_fqdn, 22)
        logging.info("Bastion Host {} is Reachable".format(config["region"]))
        print("")
    except NameError:
        print("Unable to reach the bastion host "+bastion_fqdn)
        print("There might be a connectivity issue, or a firewall blocking SSH traffic")
        raise SystemExit
    try:
        user_ocid=(config["user"])
        split_user_ocid=user_ocid.split('.')
        global clean_user_ocid
        clean_user_ocid=(split_user_ocid[4])
        global session_display_name
        session_display_name=clean_user_ocid
    except NameError:
        print("Unable to find the user OCID in the config file.")
        raise SystemExit

try:
    preflight_checks()
except Exception:
    raise SystemExit
def local_port_generator():
        port_value=random.randint(20000,50000)
        return(port_value)

def create_bastion_session():
    print("OCI Is Creating A Bastion Session.")
    global bastion_session_ocid
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
    bastion_session_ocid=bastion_session.data.id
    print("Waiting For the Session to Become Active.")
    print("")
    while True:
        session_response=bastion_client.get_session(session_id=bastion_session.data.id)
        if session_response.data.lifecycle_state == "CREATING":
            continue
        else:
            break
def existing_bastion_session():
    list_sessions_response = bastion_client.list_sessions(
        bastion_id=bastion_host_ocid,
        display_name=clean_user_ocid,
        session_lifecycle_state="ACTIVE")
    active_session=(list_sessions_response.data)
    if active_session != []: 
        global bastion_session_ocid
        bastion_session_ocid=(active_session[0].id)
        print("There is already an active bastion session. Skipping session creation.")
        print("")
    else:
        create_bastion_session()
existing_bastion_session()
def commands(type, ip_addr, remote_port):
    local_port = local_port_generator()
    if type == "SOCKS5":
        print("SOCKS5 PROXY <--MAPPED TO--> localhost:{}".format(local_port))
        cmd = "ssh", "-o", "serveraliveinterval=60", "-N", "-D", "{}:{}".format("127.0.0.1", local_port), "{}@{}".format(bastion_session_ocid, bastion_fqdn)
    if type == "LOCAL":
        print("{}:{} <--MAPPED TO--> localhost:{}".format(ip_addr, remote_port, local_port))
        cmd = ("ssh", "-o", "serveraliveinterval=60", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session_ocid, bastion_fqdn))
    return cmd
async def run_cmd():
    cmd = []
    cmd.append(commands("SOCKS5",0,0))
    while True:
        try:
            local_connections
            for (ip_addr, remote_port) in local_connections:
                cmd.append(commands("LOCAL",ip_addr,remote_port))
            break
        except:
            break
    await asyncio.gather(*[subprocess(cmds) for cmds in cmd])
async def subprocess(cmds):
    toomanyerrors=0
    while toomanyerrors<20:
        try:
            process = await asyncio.create_subprocess_exec(*cmds,
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            return_code = process.returncode
            checkin=bastion_client.get_session(session_id=bastion_session_ocid)
            session_status = checkin.data.lifecycle_state
            if return_code == 0:
                logging.info(f'Standard output: {stdout.decode().strip()}')
                toomanyerrors+=1
            if session_status != "ACTIVE":
                break
            else:
                logging.info(f'Standard error: {stderr.decode().strip()}')
                toomanyerrors+=1
                await asyncio.sleep(2)
        except Exception or RuntimeError:
            pass
    if toomanyerrors==20:
        print("Something is wrong with SSH connections to the bastion host.")
        print("Uncomment the 'logging' section of the script to get more details on the failure.")
def exit_buddy():
    while True:
        try:
            local_connections
            break
        except:
            print("")
            print("Local forwarding is not configured. This might not be a problem. ")
            print("However, if you're looking to use this script on non-SOCKS traffic . . .")
            print("Uncomment 'local_connections' in the script variables, and set your OCI private IP and port")
            break
    print("")
    print("Bastion session is cleaned up, and SSH tunnels are terminated.")
    print("Run the script again to reconnect.")
try:
    print("!!!KEEP THIS TERMINAL OPEN!!!")
    asyncio.run(run_cmd())
    print("")
    print("Bastion Session Expired.")
    print("The current session TTL is {} minutes".format(session_ttl/60))
    exit_buddy()
    quit(-1)
except KeyboardInterrupt:
    try:
        bastion_client.delete_session(session_id=bastion_session_ocid)
    except:
        pass
    exit_buddy()
    quit(-1)

#Bastion session do not support tagging, and it is not easy to get the user ID
#I'm using the name of the session as a tag, and if the user has an active session, 
# then use the exisiting session instead of creating a new one

#Maybe's in the future
# Move SSH subprocess to the asyncSSH API. https://asyncssh.readthedocs.io/en/stable/api.html#asyncssh.SSHClientConnection.forward_socks 
# I'm not sure if this is beneficial since using an SSH process works well, and is available on every operating system.
#
# It would be nice if you didn't have to set your profile to use bastions in different regions. I might be able to parse the config file and automatically set the profile based on the region.
