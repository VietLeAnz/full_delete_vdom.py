#!/usr/bin/python
# Written by Viet Le
# Feel free to use for all purposes at your own risks

# README
# The input file should be a good backup config file from the FortiGate
# The script was tested on FGT 6.2.x config version
# The script removes vdoms in the following ways
# - delete interfaces bound to deleting vdoms
# - delete vdom from GUI dashboard settings for admin users
# - delete vdom from session sync cluster FGSP
# - delete vdom from config system vdom-property
# - delete the whole vdom configuration from 'config vdom', edit <delete vdom> to the 'end'
# Other vdom related settings should be deleted manually by 'search and delete' in the Text editor, .e.g. Notepad++
# The vdom.txt file contains the vdom you want to keep in the output. I.e. vdom not in the vdom.txt will be deleted

# the following vdom related configuration will not be removed. Make sure you search the deleted vdom and edit manually.

# config system switch-interface
# config system api-user
# config system sso-admin
# config system ha
# config system fortimanager
# config system fm
# config system central-management
# config system vdom-exception
# config extender-controller extender

import re, os.path
import sys, getopt

# backup file
backup_file = 'F:\\Projects\\in\dummy-fw01_20220224_1800.conf'
# output file
output_file = 'F:\\Projects\\out\\dummy-fw01_20220224_1800_new.conf'
# vdom to keep
vdom_file = 'F:\\Projects\\in\\vdom.txt'


def usage():
    """ Used to print Syntax
    """
    print("Syntax:\n\t{} -i <backup_file> -o <output_file> -v <vdom_file>".format(os.path.basename(__file__)))
    print("Examples:\n\t{} -i backup-config.conf -o outfile.conf -v vdom.txt".format(os.path.basename(__file__)))


def main(argv):
    global backup_file
    global output_file
    global vdom_file

    try:
        opts, args = getopt.getopt(argv, "hi:o:v:", ["ifile=", "ofile=", "vfile="])
    except getopt.GetoptError:
        print("Error:\n\tInvalid commands")
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-i", "--ifile"):
            backup_file = arg
        elif opt in ("-o", "--ofile"):
            output_file = arg
        elif opt in ("-v", "--vfile"):
            vdom_file = arg


if __name__ == "__main__":
    # main(sys.argv[1:])

    print("Please wait! I am working on {}".format(backup_file))
    print('*' * 60)
    hit = 0  # count number of vdoms were split
    vdoms = []  # vdom list place holder

    try:
        with open(vdom_file,'r') as vdom_list:
            vdoms = vdom_list.read().split()

    except IOError as e:
        print("Input file error: {} or file {} does not exist.".format(e.strerror, vdom_file))
        usage()
        sys.exit()


    try:
        with open(backup_file, 'r') as config_file:
            # vdoms = ["root","roc","space","ext-agency","ops-voip","dmz","management","vcs","cs","inter-vpn"]
            # vdoms = ["roc","root","cs-mgmt","escada-b","ext-agency","sec-service","ict","escada-a","space","tc-voip","ticketing","oss","ctip","ip-pa","lvl-xg-cctv","sec-mgmt","new-ip-cctv","escada-ws","bms","ops-voip","old-cctv","bsn","dmz","sydnet","env-mon","management","vcs","wan","cmn","cmn-test","ecrl-ccs-b","c4-hci","etg","srs","ss-dmz","nm-dash","cctv-rr","int-agency","siglan","cs","dtrs","tnt","ecrl-ccs-a","dtrs-disp","spi","vrn","ss-mgmt","inter-vpn"]
            vdom_block, interface_cmd, admin_cmd, vdom_prop, cluster_sync, keep_vdom = False, False, False, False, False, False
            vdom_cmd, interface, admin_vdom_list, copied_vdom = [], [], [], []
            last_command, vdom_name = '', ''
            line = 0
            outfile = open(output_file, 'w')
            for command_line in config_file:
                line += 1           # for troubleshooting - what line the file read up to
                if re.findall(r'config vdom', command_line):  # to check if configuration for the previous vdom config ends
                    vdom_block = True
                    if vdom_name in vdoms:                  # if vdom is kept, write to file
                        for vdom_command in vdom_cmd:       # write all the command read so far.
                            outfile.write(vdom_command)
                    vdom_cmd.clear()                    # clear vdom content and for the next vdom
                elif re.findall(r'config system interface', command_line):  # tell the script we are in the interfaces
                    interface_cmd = True
                    admin_cmd = False
                    cluster_sync = False
                    outfile.write(command_line)   # write this command to file
                elif re.findall(r'^config system admin', command_line): # we are in the admin user settings
                    admin_cmd = True
                    interface_cmd = False
                    cluster_sync = False
                    outfile.write(command_line)
                elif re.findall(r'config system cluster-sync',command_line): #we are in the cluster-sync settings
                    cluster_sync = True
                    interface_cmd = False
                    admin_cmd = False
                    outfile.write(command_line)
                elif re.findall(r'config system vdom-property',command_line):
                    vdom_prop = True
                    cluster_sync = False
                    interface_cmd = False
                    admin_cmd = False
                    outfile.write(command_line)
                elif vdom_block:            # while we are in the vdom block (config vdom, edit <vdom name>, end)
                    if re.findall(r'^edit .*',command_line):
                        vdom_name = command_line.strip(' ').strip('\n')[5:]  # extracts vdom name from the commmand
                        if vdom_name in vdoms:              # if vdom should be kept
                            if last_command != 'next\n':    # if the last command is not next then vdom command starts
                                vdom_cmd.append("config vdom\n")  # need to write this command to start the vdom config
                            vdom_cmd.append(command_line)   # write the 'edit <vdom>' to file
                            keep_vdom = True
                        else:
                            keep_vdom = False
                            continue        # go to the next line in file reading without processing further
                    elif re.findall(r'^next',command_line):   # this tell we are in the vdom creating block
                        last_command = command_line             # track the last command
                        if vdom_name in vdoms:
                            vdom_cmd.append(command_line)   # write this 'next' to output file
                    elif re.findall(r'^end',command_line):
                        if vdom_name in vdoms:
                            vdom_cmd.append("end\n")            # write this 'end' to the buffer
                        if last_command == 'next\n':        # if the last command is 'next' it means the vdom creation ends
                            for vdom_command in vdom_cmd:
                                outfile.write(vdom_command) # write this to the output file
                            # last_command = ''       # clear the last command, usually 'next'
                            vdom_block = False      # we are not in vdom block anymore
                            vdom_cmd.clear()        # clear all the commands within vdom block
                        last_command = ''       # clear the last command, usually 'next'
                    elif keep_vdom:             # if vdom is kept, buffer this command for writing later to output.
                        vdom_cmd.append(command_line)
                elif interface_cmd:             # we are in the system interface settings
                    interface.append(command_line)      # buffer the interface commands
                    if re.findall(r'set vdom \".*\"',command_line):         # check the vdom name
                        vdom_name = command_line.strip(' ').strip('\n')[10:].strip('"')     # from the command line
                        if vdom_name in vdoms:      # if vdom is kept, mark it
                            keep_vdom = True
                        else:
                            keep_vdom = False
                            interface.clear()   # ignore related interface setting for the vdom to be deleted
                            continue            # go to the next line in config file without processing further
                    elif re.findall(r'\s{4}next',command_line):     # end of the interface settings
                        if keep_vdom:
                            for setup in interface:                 # write the interface settings to file for kept vdom
                                outfile.write(setup)
                        interface.clear()                   # clear the buffer
                    elif re.findall(r'^end',command_line):      # this command tells the interface settings finished
                        interface_cmd = False
                        outfile.write(command_line)             # write this 'end' command to the file
                elif admin_cmd:                                 # we are in admin user setting
                    if re.findall(r'set vdom \".*\"',command_line):     # extract vdom name from the list of vdoms
                        new_vdom_list = ''                              # keep list of vdom in string
                        space_num = command_line.index('s')
                        admin_vdom_list = command_line.strip(' ').strip('\n')[9:].split(' ') # put vdom list in array
                        for value in admin_vdom_list:
                            value = value.strip('"')
                            if value in vdoms:              # build the new vdom list after removing deleted vdoms
                                new_vdom_list += ' "' + value + '"'
                        if new_vdom_list != '':             # write the new vdom list to file
                            outfile.write(" " * space_num + 'set vdom' + new_vdom_list + '\n')
                        continue                        # go to the next line in config file without processing further
                    elif re.findall(r'^end',command_line):      # this is the end of system interface settings
                        admin_cmd = False               # mark the end of admin user settings
                    outfile.write(command_line)         # write other settings to output file
                elif cluster_sync:                      # we are in cluster_sync config, similar to admin user
                    if re.findall(r'set syncvd \".*\"',command_line):
                        new_vdom_list = " " * 8 + "set syncvd"
                        admin_vdom_list = command_line.strip(' ').strip('\n')[11:].split(' ')
                        for value in admin_vdom_list:
                            value = value.strip('"')
                            if value in vdoms:
                                new_vdom_list += ' "' + value + '"'
                        outfile.write(new_vdom_list + '\n')
                    elif re.findall(r'^end',command_line):
                        outfile.write(command_line)
                        cluster_sync = False            # mark the end of config cluster sync block
                    else:
                        outfile.write(command_line)
                elif vdom_prop:
                    if re.findall(r'edit \".*\"',command_line):
                        vdom_name = command_line.strip(' ').strip('\n')[6:].strip('"')
                        if vdom_name in vdoms:
                            copied_vdom.append(vdom_name)
                            keep_vdom = True
                            outfile.write(command_line)
                        else:
                            keep_vdom = False
                    elif re.findall(r'^end',command_line):
                        vdom_prop = False
                        outfile.write(command_line)
                    elif keep_vdom:
                        outfile.write(command_line)
                else:
                    outfile.write(command_line)
            if len(vdom_cmd) > 0 and vdom_name in vdoms:   # flush the last vdom to output file if vdom need to keep
                for vdom_command in vdom_cmd:
                    outfile.write(vdom_command)
            hit = len(copied_vdom)        # number of vdoms in vdom.txt file
            outfile.close()         # close the output file object
    except IOError as e:
        print("Input file error: {} or file {} does not exist.".format(e.strerror, backup_file))
        usage()
        sys.exit()
    if hit > 0:
        print("Results: {} vdoms below were copied to {}\n".format(int(hit), output_file))
        print("(Vdoms: ", end='')
        for vdom in copied_vdom:
            print(vdom, end=',')
        print(")")
        print("""\t\nNotes:
            The following vdom related configuration will not be edited/remove.
            Make sure you search the deleted/edit the objects manually in the output file.
            
            # config system switch-interface
            # config system api-user
            # config system sso-admin
            # config system ha
            # config system fortimanager
            # config system fm
            # config system central-management
            # config system vdom-exception
            # config extender-controller extender
            """)
    else:
        print("There is no vdom in the input file {}".format(backup_file))

