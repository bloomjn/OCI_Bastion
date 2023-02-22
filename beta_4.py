###Required Variables###
bastion_host_ocid="ocid1.bastion.oc1.iad.amaaaaaac3adhhqa5z4bkw5hvtwu7cyf4bqgprl665qjwyrnteucyx2f46cq" #OCID of the Bastion Host you want to create sessions with on OCI.

###Optional Variables###
#oci_config_location="/Users/jake/.oci/config" #OCI Configuration File that was generated from the API Key in the OCI GUI. Change if this is not the default
#pub_key_file=r"/Users/Jake/.ssh/id_rsa.pub" #Specify the full path of your SSH public key. This is not the same thing as your OCI RSA KEY. This file is most likely named 'id_rsa.pub' in your .ssh folder.
session_ttl=1800 #30 Minutes by default, and gives a good balance for allowing stale sessions to close and allow other users to connect to the Bastion host.
#local_connections=[("10.0.0.254", 8000),("10.0.1.130", 3389),("10.0.0.3", 21),("10.0.0.254", 22)] #Set OCI_PRIVATE_IP and OCI_DEST_PORT for non-SOCKS5 applications to do local forwarding.
##########################

###MODULES###
import random, hashlib, re, asyncio, subprocess, socket, logging, argparse, time, os, sys
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) #Turn this on if you're trying to debug the script.
try: 
    import oci
    logging.info("OCI module import is succuessful")
except ImportError: 
    print("Failed to import OCI SDK. Make sure it is installed and accessible.")
    print("https://pypi.org/project/oci/")
    print("Run this command if you want to skip some reading.")
    print("pip3 install oci")
    raise SystemExit
##############   

###SCRIPT###
CLI=argparse.ArgumentParser(description= "Usage: python3 pseudovpn.py -b 'bastionhostOCID' -l 'OCI_PRIVATE_IP_1 PORT_1 -l OCI_PRIVATE_IP_2 PORT_2 -r")
CLI.add_argument("--bastion_ocid","-b", type=str,help="add your Bastion OCID")
CLI.add_argument("--run-forever", action='store_false',help="Set this flag to create bastion sessions indefinitely")
CLI.add_argument("--local_connections", "-l", type=str, action="append", nargs="+",help="USAGE: -l OCI_PRIVATE_IP OCI_PORT")
args=CLI.parse_args()
if args.bastion_ocid != None:
    bastion_host_ocid=args.bastion_ocid
if args.local_connections != None:
    local_connections_list=args.local_connections
    local_connections=[tuple(x) for x in local_connections_list]
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
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
    global pub_key_file
    try:
        pub_key_file
    except:
        home_dir=os.path.expanduser('~')
        pub_key_file=(os.path.join(home_dir,".ssh","id_rsa.pub"))
        #ssh_pub='/.ssh/id_rsa.pub'
        #pub_key_file=home_dir+ssh_pub
        try:
            os.path.isfile(pub_key_file)
        except:
            print("Unable to find your public SSH key.")
            print("Set the 'pub_key_file' variable in the script if your key is not in the standard location.")
            print("Or run 'ssh-keygen' in your shell and you should be good to go.")
            print("This script currently doesn't support encrypted keys.")
    global oci_config_location
    try:
        oci_config_location
    except:
        home_dir=os.path.expanduser('~')
        oci_config_location=(os.path.join(home_dir,".oci","config"))
        #oci_file='/.oci/config'
        #oci_config_location=home_dir+oci_file
        try:
            os.path.isfile(oci_config_location)
        except:
            print("Unable to find the default location for your OCI config")
            print("It should be located in at ~/.oci/config")
            print("I recommend using this file location, because you can use it for other purposes than this script (OCI CLI)")
            print("Update the 'oci_config_location' variable if you want to use a non-default file path.")
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
        global identity
        config = oci.config.from_file(oci_config_location)
        oci.config.validate_config(config)
        identity = oci.identity.IdentityClient(config) #Get User Info
    except Exception as e:
        print("There is an error with your OCI config file")
        print("")
        print(oci.config.InvalidConfig(e))
        raise SystemExit
    try:
        splitter=bastion_host_ocid.split('.')
        bastion_region_code=splitter[3]
        available_regions = identity.list_regions()
        for region in available_regions.data:
            region_key_val=region
            if region_key_val.key == bastion_region_code.upper():
                bastion_region_name=(region_key_val.name)
                config["region"] = bastion_region_name
    except:
        print("Your OCI config file does not have a profile associated with the {} region".format(bastion_region_name))
        print("Create an API key for this region and append the configuration to your existing OCI config file.")
        raise Exception
    uniquestring=(bastion_host_ocid + config["user"])
    hash=hashlib.sha256(bytes(uniquestring, encoding='utf8')).hexdigest()
    seed_int=re.sub('[^0-9]', '', hash)
    random.seed(seed_int)
    logging.info("Seed Set")
    print("Authenticating OCI User...")
    try:      
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
bastion_client = oci.bastion.BastionClient(config)
def local_port_generator():
        port_value=random.randint(20000,50000)
        return(port_value)
def create_bastion_session():
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
        print("OCI Is Creating A Bastion Session.")
        print("Waiting For the Session to Become Active.")
        print("")
        create_bastion_session()
existing_bastion_session()
def commands(type, ip_addr, remote_port):
    local_port = local_port_generator()
    if type == "SOCKS5":
        print("SOCKS5 PROXY <--MAPPED TO--> localhost:{}".format(local_port))
        cmd = "ssh", "-o", "HostKeyAlgorithms=ssh-rsa", "-o", "PubkeyAcceptedKeyTypes=ssh-rsa", "-o", "serveraliveinterval=60", "-o", "StrictHostKeyChecking no", "-N", "-D", "{}:{}".format("127.0.0.1", local_port), "{}@{}".format(bastion_session_ocid, bastion_fqdn)
    if type == "LOCAL":
        print("{}:{} <--MAPPED TO--> localhost:{}".format(ip_addr, remote_port, local_port))
        cmd = ("ssh", "-o", "HostKeyAlgorithms=ssh-rsa", "-o", "PubkeyAcceptedKeyTypes=ssh-rsa", "-o", "serveraliveinterval=60", "-o", "StrictHostKeyChecking no", "-N", "-L", "{}:{}:{}".format(local_port, ip_addr, remote_port), "{}@{}".format(bastion_session_ocid, bastion_fqdn))
    return cmd
async def run_cmd():
    global cmd
    try:
        cmd
        new_cmds = []
        for cmd in cmd:
            user_host = cmd[-1].split('@')
            user_host[0] = bastion_session_ocid
            new_user_host = '@'.join(user_host)
            new_cmd = cmd[:-1] + (new_user_host,)
            new_cmds.append(new_cmd)
        cmd=new_cmds
    except:
        cmd = []
        if not cmd:
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
    while toomanyerrors<10:
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
                await asyncio.sleep(1)
        except RuntimeError:
            pass
        except Exception:
            quit(-1)
    if toomanyerrors==10:
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
    if args.run_forever == False:
        starttime=time.time()
        print("You will be continously connected to the Bastion until the script is closed.")
        print("Sessions will be automatically created for you in the background.")
        print("You might see a temporary disconnect while a new session is created.")
        print("")
        while True:
            try:
                session_state=bastion_client.get_session(session_id=bastion_session_ocid)
                if session_state.data.lifecycle_state == "ACTIVE":
                    asyncio.run(run_cmd())
                if session_state.data.lifecycle_state != "ACTIVE":
                    create_bastion_session()
            except RuntimeError:
                pass
            except KeyboardInterrupt:
                runtime=starttime-time.time()
                if runtime>int(60):
                    print("The runtime of the script was {} minutes".format(runtime/60))
                try:
                    bastion_client.delete_session(session_id=bastion_session_ocid)
                except RuntimeError:
                    pass
                print("")
                exit_buddy()
                quit(-1)

    else:
        asyncio.run(run_cmd())
        print("")
        print("Bastion Session Expired.")
        print("The current session TTL is {} minutes".format(session_ttl/60))
        exit_buddy()
        quit(-1)
except KeyboardInterrupt:
    try:
        bastion_client.delete_session(session_id=bastion_session_ocid)
    except RuntimeError:
        pass
    print("")
    exit_buddy()
    quit(-1)
