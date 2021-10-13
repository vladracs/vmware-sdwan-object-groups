# Author: Vladimir França de Sousa - vfsprivate@protonmail.com
#
# Python script that takes a raw Cisco Object-Group config file
# and parse it into a readable dictonary to be used as input to configure
# VMware SASE SD-WAN Orchestrator
#
# Note
# VCO names are not case sensitive, so GROUP-1 = group-1
# in case Cisco configuration has groups with similar name ,
# we will end up overwriting the group
#
# VCO only accepts 255 IPs in a single Network Address Group

import string
import argparse
import csv
import os
import requests
import sys
import traceback
import json
from copy import deepcopy
import ipaddress
from time import sleep
seconds = 2 #avoid vco rate limit
sleep(seconds)

token = os.environ['VCO_TOKEN']
vco_url = 'https://' + os.environ['VCO_HOSTNAME'] + '/portal/rest/'
headers = {"Content-Type": "application/json", "Authorization": token}
######## VCO API methods
get_enterprise = vco_url + 'enterprise/getEnterprise'
get_edgelist = vco_url+'enterprise/getEnterpriseEdgeList'
get_edgeconfig = vco_url + 'edge/getEdgeConfigurationStack'
update_edgeconfig = vco_url+'configuration/updateConfigurationModule'
edge_prov = vco_url+'edge/edgeProvision'
get_profiles =vco_url + 'enterprise/getEnterpriseConfigurationsPolicies'
create_profile = vco_url+'configuration/cloneEnterpriseTemplate'
getObjectGroups = vco_url+'enterprise/getObjectGroups'
updateObjectGroup = vco_url+'enterprise/updateObjectGroup'
insertObjectGroup = vco_url+'enterprise/insertObjectGroup'
objects_template={"name":"netgroups","description":"desc","type":"address_group","data":[],"id":1}
sobjects_template={"name":"portgroups","description":"desc","type":"port_group","data":[],"id":1}

def insert_group(row,eid):
    print(row["name"],end="")
    print(" group not found on VCO - Inserting New Group")
    new_obj=deepcopy(objects_template)
    new_obj['name']= row["name"]
    new_obj['description']= row["description"]
    #build data from dictionary
    new_obj['data'] =[]
    if not row["host"]==[]:
            print("hosts addresses to configure")
            for i in range(0, len(row["host"])):
                addr={"rule_type":"exact","mask":"255.255.255.255","ip":row["host"][i]}
                new_obj['data'].append(addr)
    if not row["subnet"]==[]:
            print("subnet addresses to configure")
            subn=row["subnet"][0].split(" ")
            addr={"rule_type":"netmask","mask":subn[1],"ip":subn[0]}
            new_obj['data'].append(addr)
    if not row["host range"]==[]:
            print("host range to configure")
            arange=row["host range"][0].split(" ")
            iplow = ipaddress.IPv4Address(arange[0])
            iphigh = ipaddress.IPv4Address(arange[1])
            for ip_int in range(int(iplow), int(iphigh)+1):
                addr={"rule_type":"exact","mask":"255.255.255.255","ip":str(ipaddress.IPv4Address(ip_int))}
                new_obj['data'].append(addr)
    params = new_obj
    objgroups = requests.post(insertObjectGroup, headers=headers, data=json.dumps(params))
    #print(objgroups.json())

def update_group(file_groups,group,eid):
    print("Group %s found - updating it"%group["name"])
    port_group_id = group["id"]
    new_obj=deepcopy(group)
    new_obj['description']= file_groups["description"]
    if not file_groups["host"]==[]:
                print("hosts ip addresses to configure")
                for i in range(0, len(file_groups["host"])):
                    #check for duplicates
                    notdup=True
                    for j in range(0, len(group['data'])):
                        if file_groups["host"][i]==group['data'][j]['ip']:
                            notdup=False
                    if notdup:
                        addr={"rule_type":"exact","mask":"255.255.255.255","ip":file_groups["host"][i]}
                        new_obj['data'].append(addr)
    if not file_groups["subnet"]==[]:
                print("subnet addresses to configure")
                subn=file_groups["subnet"][0].split(" ")
                ### check for duplicates
                notdup=True
                for j in range(0, len(group['data'])):
                    if subn[0]==group['data'][j]['ip'] and subn[1]==group['data'][j]['mask']:
                        notdup=False
                if notdup:
                    addr={"rule_type":"netmask","mask":subn[1],"ip":subn[0]}
                    new_obj['data'].append(addr)
    if not file_groups["host range"]==[]:
                print("host range to configure")
                arange=file_groups["host range"][0].split(" ")
                iplow = ipaddress.IPv4Address(arange[0])
                iphigh = ipaddress.IPv4Address(arange[1])
                for ip_int in range(int(iplow), int(iphigh)+1):
                    notdup=True
                    for j in range(0, len(group['data'])):
                        if ip_int==group['data'][j]['ip']:
                            notdup=False
                    if notdup:
                        addr={"rule_type":"exact","mask":"255.255.255.255","ip":str(ipaddress.IPv4Address(ip_int))}
                        new_obj['data'].append(addr)
    params=new_obj
    objgroups = requests.post(updateObjectGroup, headers=headers, data=json.dumps(params))
    #print(objgroups.json())

def swap_port(argument):
    #print(argument)
    with open('port-names.json', 'r') as myfile:
        data=myfile.read()
        obj = json.loads(data)

        for i in range(0, len(obj)):
            if (obj[i]['service'])==str(argument):
                return obj[i]['port']
    return argument

def sinsert_group(row,eid):
    print(row["name"],end="")
    print(" group not found on VCO - Inserting New Group")
    new_obj=deepcopy(sobjects_template)
    new_obj['name']= row["name"]
    new_obj['description']= row["description"]
    #build data from dictionary
    new_obj['data'] =[]
    if not row["tcp"]==[]:
            print("tcp ports to configure")
            for i in range(0, len(row["tcp"])):
                ### account for when only protocol is configured (tcp)
                if not row["tcp"][i]=="no-port":
                        portx=swap_port(row["tcp"][i]) #Convert strings to port
                        port={"proto":6,"port_low":portx,"port_high":portx}
                        new_obj['data'].append(port)
                else:
                    new_obj['data']=[]
    if not row["udp"]==[]:
            print("udp ports to configure")
            for i in range(0, len(row["udp"])):
                if not row["udp"][i]=="no-port":
                    portx=swap_port(row["udp"][i])
                    port={"proto":17,"port_low":portx,"port_high":portx}
                    new_obj['data'].append(port)
                else:
                    new_obj['data']=[]
    if not row["tcp range"]==[]:
            print("tcp range to configure")
            rports=row["tcp range"][0].split(" ")
            port={"proto":6,"port_low":rports[0],"port_high":rports[1]}
            new_obj['data'].append(port)
    if not row["udp range"]==[]:
            print("udp range to configure")
            low=row["udp range"][0].split(" ")[:1]
            high=row["udp range"][0].split(" ")[1]
            port={"proto":17,"port_low":rports[0],"port_high":rports[1]}
            new_obj['data'].append(port)
    params = new_obj
    objgroups = requests.post(insertObjectGroup, headers=headers, data=json.dumps(params))
    #print(objgroups.json())

def supdate_group(file_groups,group,eid):
    print("Group %s found - updating it"%group["name"])
    port_group_id = group["id"]
    new_obj=deepcopy(group)
    new_obj['id']= group["id"]
    new_obj['name']= group["name"].lower()
    new_obj['description']= file_groups["description"]
    if not file_groups["tcp"]==[]:
          print("tcp ports to configure")
          for i in range(0, len(file_groups["tcp"])):
              if not file_groups["tcp"][i]=="no-port":
                  #check for duplicates
                  notdup=True
                  portx=swap_port(file_groups["tcp"][i]) #Convert strings to port
                  for j in range(0, len(group['data'])):

                      if portx==group['data'][j]['port_low'] and group['data'][j]['proto']==6:
                        notdup=False
                        print("dup found")
                  if notdup:
                      #print("unique found")
                      port={"proto":6,"port_low":portx,"port_high":portx}
                      new_obj['data'].append(port)
              else:
                print("protocol without port not supported")
    if not file_groups["udp"]==[]:
          print("udp ports to configure")
          for i in range(0, len(file_groups["udp"])):
              if not file_groups["udp"][i]=="no-port":
                  #check for duplicates
                  notdup=True
                  portx=swap_port(file_groups["udp"][i])
                  for j in range(0, len(group['data'])):

                      if portx==group['data'][j]['port_low'] and group['data'][j]['proto']==17:
                        notdup=False
                        print("dup found")
                  if notdup:
                      port={"proto":17,"port_low":portx,"port_high":portx}
                      new_obj['data'].append(port)
              else:
                  print("protocol without port not supported")
    if not file_groups["tcp range"]==[]:
          print("tcp range to configure")
          rports=file_groups["tcp range"][0].split(" ")
          #check for duplicates
          notdup=True
          for j in range(0, len(group['data'])):
              if group['data'][j]['proto']==6 and rports[0]==group['data'][j]['port_low'] and rports[1]==group['data'][j]['port_high']:
                      notdup=False
                      print("dup found")
          if notdup:
            print("unique entry found")
            port={"proto":6,"port_low":rports[0],"port_high":rports[1]}
            new_obj['data'].append(port)
    if not file_groups["udp range"]==[]:
          print("udp range to configure")
          low=file_groups["udp range"][0].split(" ")[:1]
          high=file_groups["udp range"][0].split(" ")[1]
          notdup=True
          for j in range(0, len(group['data'])):
                  if group['data'][j]['proto']==17 and rports[0]==group['data'][j]['port_low'] and rports[1]==group['data'][j]['port_high']:
                      notdup=False
                      print("dup found")
          if notdup:
              port={"proto":17,"port_low":rports[0],"port_high":rports[1]}
              new_obj['data'].append(port)
    params=new_obj
    #print(new_obj)
    objgroups = requests.post(updateObjectGroup, headers=headers, data=json.dumps(params))
    print(objgroups.json())
def find_velo_enterpriseId():
	#Fetch enterprise id convert to JSON
	eid=0
	try:
         enterprise = requests.post(get_enterprise, headers=headers, data='')

	except Exception as e:
	   print('Error while retrivieng Enterprise')
	   print(e)
	   sys.exit()
	ent_j = enterprise.json()
	eid=ent_j['id']
	print('Enterprise Id = %d'%(eid))
	return eid
def parse_network_groups(file) -> list[dict]:
    groups = []
    for line in file:
        line = line.strip()
        if line.startswith("Network object group "):
            current_group = {"name": line.replace("Network object group ",""), "description":"my desc","host": [],"subnet": [],"host range": []}
            groups.append(current_group)
        elif line.startswith("Description "):
            current_group["description"]=line.replace("Description ","")
        elif line.startswith("host"):
            current_group["host"].append(line.replace("host ",""))
        elif line.startswith("subnet "):
            current_group["subnet"].append(line.replace("subnet ",""))
        elif line.startswith("range "):
            current_group["host range"].append(line.replace("range ",""))
        elif len(line.strip())==0:
            break
        else:
            raise NotImplementedError("Cannot parse " + line)
    return groups
def parse_service_groups(file) -> list[dict]:
    groups = []
    for line in file:
        line = line.strip()
        if line.startswith("Service object group "):
            current_group = {"name": line.replace("Service object group ",""), "description":"my desc","tcp": [],"udp": [],"tcp range": [],"udp range": [],"icmp": [],}
            groups.append(current_group)
        elif line.startswith("Description "):
            current_group["description"]=line.replace("Description ","")
        elif line.startswith("tcp eq "):
            current_group["tcp"].append(line.replace("tcp eq ",""))
        elif line.startswith("udp eq "):
            current_group["udp"].append(line.replace("udp eq ",""))
        elif line.startswith("tcp range "):
            current_group["tcp range"].append(line.replace("tcp range ",""))
        elif line.startswith("udp range "):
            current_group["udp range"].append(line.replace("udp range ",""))
        elif line.startswith("tcp"):
                current_group["tcp"].append(line.replace("tcp","no-port"))
        elif line.startswith("udp"):
                current_group["udp"].append(line.replace("udp","no-port"))
        elif line.startswith("icmp "):
            current_group["icmp"].append(line)
        elif len(line.strip())==0:
            break
        else:
            raise NotImplementedError("Cannot parse " + line)
    return groups
#Add description (and subnet keyword when needed) to all groups  and split in 2 files (address and port groups)
def parse_file(ifile):
    with open(ifile, 'r+') as f:
        with open('ngroups.txt', 'w') as n_file:
         with open('sgroups.txt', 'w') as s_file:
            lines = f.readlines()
            for i in range(0, len(lines)):
                if not (len(lines[i])==0):
                    if (lines[i].startswith("Network") and  lines[i+1].startswith(" Description")):
                        n_file.write(lines[i])
                        n_file.write(lines[i+1])
                    if (lines[i].startswith("Service") and  lines[i+1].startswith(" Description")):
                        s_file.write(lines[i])
                        s_file.write(lines[i+1])
                    if lines[i].startswith("Network") and not lines[i+1].startswith(" Description"):
                        n_file.write(lines[i])
                        n_file.write(" Description N-ADDED")
                        n_file.write("\n")
                    if lines[i].startswith("Service") and not lines[i+1].startswith(" Description"):
                        s_file.write(lines[i])
                        s_file.write(" Description S-ADDED")
                        s_file.write("\n")
                    if not lines[i].startswith("Network") and not lines[i].startswith(" Description") and not lines[i].startswith("Service"):
                        if lines[i].startswith(" tcp") or lines[i].startswith(" udp") or lines[i].startswith(" icmp"):
                            s_file.write(lines[i])
                        elif lines[i].startswith(" host") or  lines[i].startswith(" range"):
                            n_file.write(lines[i])
                        elif not lines[i]=="\n":
                            n_file.write(" subnet")
                            n_file.write(lines[i])
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="name of the file with Object Groups Configuration")
    parser.add_argument("-p", "--provision", action='store_true', help="Option: Provision Object Groups in the VCO",default = False)
    args = parser.parse_args()

### clean up config first
    parse_file(args.file)
    #parse service groups from new txt file
    with open('ngroups.txt', 'r+') as n_file:
        grps=parse_network_groups(n_file)
        with open('ngroups-clean.txt', 'w') as nt_file:
            for x in range(len(grps)):
                nt_file.write(json.dumps(grps[x]))
                nt_file.write("\n")
    #parse network groups from new txt file
    with open('sgroups.txt', 'r+') as s_file:
        grps=parse_service_groups(s_file)
        with open('sgroups-clean.txt', 'w') as st_file:
            for x in range(len(grps)):
                st_file.write(json.dumps(grps[x]))
                st_file.write("\n")
#### Configure Groups in VCO
    if(args.provision):
        eid = find_velo_enterpriseId()
            ### Configure Network/Address Groups
        with open("ngroups-clean.txt") as jfile: #file contain lines with dictionaries
         for row in jfile:
             file_groups = json.loads(row.replace("'", '"'))
             params = {'enterpriseId': eid,"type":"address_group"}
             resp = requests.post(getObjectGroups, headers=headers, data=json.dumps(params))
             vcogroups=resp.json()
        #Check if Port Group Already exists - update, if not insert a new group
             update=False
             for group in vcogroups:
                    if group["name"].lower() == file_groups["name"].lower():
                        update_group(file_groups,group,eid)
                        update=True
                        break
             if(update==False):
                        insert_group(file_groups,eid)
        ### Configure Service/Port Groups
        with open("sgroups-clean.txt") as jfile: #file contain lines with dictionaries
         for row in jfile:
            file_groups = json.loads(row.replace("'", '"'))
            params = {'enterpriseId': eid,"type":"port_group"}
            resp = requests.post(getObjectGroups, headers=headers, data=json.dumps(params))
            vcogroups=resp.json()
          #Check if Port Group Already exists - update, if not insert a new group
            update=False
            for group in vcogroups:
                   if group["name"].lower() == file_groups["name"].lower():
                       supdate_group(file_groups,group,eid)
                       sleep(seconds)
                       update=True
                       break

            if(update==False):
                       sinsert_group(file_groups,eid)
                       sleep(seconds)

if __name__ == "__main__":
    main()
