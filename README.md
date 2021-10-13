# vmware-sdwan-object-groups
Simple Python script that reads a text file with Cisco Routers raw address and services groups configuration and builds object groups in vmware sd-wan orchestrator 

 Not to be considered as best practices in using VMware VCO API
 Meant to be used in Lab environments - Please test it and use at your own risk

 please note that VMWare API and Support team - do not guarantee this samples
 It is provided - AS IS - i.e. while we are glad to answer questions about API usage
 and behavior generally speaking, VMware cannot and do not specifically support these scripts

 Compatible with api v1 of the vmware sd-wan vco api
 using tokens to authenticate

 Note that are current a few features missing in the vmware sd-wan object-group to be 1:1 compatible with Cisco's address and Service groups.
 These will be addressed in future releases of the sd-wan software:
 Only TCP and UDP support
 Also it is not possible to define protocols without ports (ie. tcp or udp, and only tcp port 22, tcp port 1000-2000 are possible)
