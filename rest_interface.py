#!/bin/python

import sys, getopt, purestorage, json

def usage():
   print '{} [ -a | --array ] <array_name> [ -p | --password ] <api token> [ -f | --function ] <function name> [-v | --verbose]'.format(sys.argv[0])
   print 'where <function name> can be:'
   print '      list_luns [-l | --lun_name] <comma separated list of lun names (no spaces!)>'
   print '      list_hosts [-h | --host_name] <comma separated list of hostnames (no spaces!)>'
   print '      list_hostgroups'
   print ''
   print '      create_lun [-l | --lun_name] <lun name> [-s | --lun_size] <lun size>'
   print '                                                      where <lun size> can be in G or T (eg. 1T, 20G)'
   print '      create_host [ -h | --host_name ] <hostname> [ -w | --wwn ] <comma separated list of WWNs (no spaces!)>'
   print '      create_hostgroup [ -g | --group_name ] <hostgroup_name>'
   print ''
   print '      add_host_to_hostgroup [ -h | --host_name ] <comma separated list of hostnames (no spaces!)> [ -g | --group_name ] <hostgroup_name>'
   print '      add_lun_to_hostgroup [ -l | --lun_name ] <lun name> [ -g | --group_name ] <hostgroup_name>'
   print '      add_lun_to_host [ -l | --lun_name ] <lun_name> [ -h | --host_name ] <hostname>'
   print ''
   print '      remove_host_from_hostgroup [ -h | --host_name ] <comma separated list of hostnames (no spaces!)> [ -g | --group_name ] <hostgroup_name>'
   print '      remove_lun_from_host [ -l | --lun_name ] <lun name> [ -h | --host_name ] <hostname>'
   print '      remove_lun_from_hostgroup [ -l | --lun_name ] <lun name> [ -g | --group_name ] <hostgroup_name>'
   print ''
   print '      delete_host [-h --host_name ] <hostname>'
   print '      delete_hostgroup [-g | --group_name ] <hostgroup_name>'
   print '      delete_lun [ -l | --lun_name ] <lun_name>'
   print ''
   print '-v | --verbose:  will give you more detail relating to that function.'
   print '                 without "verbose" any successful actions (creates, adds etc) will simply exit with a 0 return code'
   sys.exit(2)

def main(argv):
   array_name = ''
   api_token = ''
   verbose = False
   try:
      opts, args = getopt.getopt(argv,"?h:l:a:p:f:s:vw:g:",["help", "host_name=", "lun_name=", "array=","password=","function=","lun_size=","verbose","wwn=","group_name="])
   except:
      print str(getopt.GetoptError)
      usage()
   for opt, arg in opts:
      if opt in ("-?", "--help"):
         usage()
      elif opt in ("-a", "--array"):
         array_name = arg
      elif opt in ("-p", "--password"):
         api_token = arg
      elif opt in ("-f", "--function"):
         function = arg
      elif opt in ("-h", "--host_name"):
         host_name = arg
      elif opt in ("-w", "--wwn"):
         wwn_list = arg
      elif opt in ("-l", "--lun_name"):
         lun_name = arg
      elif opt in ("-g", "--group_name"):
         group_name = arg
      elif opt in ("-s", "--lun_size"):
         lun_size = arg
      elif opt in ("-v", "--verbose"):
         verbose = True

# If no function is specified then send a usage message
   try:
      function
   except:
      print "ERROR: You must specify a function to perform"
      usage()
   
   # We need the following to prevent a security warning
   import requests 
   from requests.packages.urllib3.exceptions import InsecureRequestWarning
   requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

   array = purestorage.FlashArray(array_name, api_token=api_token)
#   
   if function == 'list_luns':
      try:
         lun_name
      except:
         response=array.list_volumes()
         if verbose:
            print("%-28s%-24s%-26s%s" % ("Name", "Size in GB", "Created", "Serial"))
            for x in range(len(response)):
               print("%-28s%-24s%-26s%s" % (response[x]['name'], response[x]['size']/1024/1024/1024, response[x]['created'], response[x]['serial']))
         else:
            for x in range(len(response)):
               print response[x]['name']
      else:
         response=array.list_volumes(names=lun_name, connect=True)
         if verbose:
            print("%-28s%-24s%-26s%s" % ("Name", "Size in GB", "Host Name", "Host Group"))
            for x in range(len(response)):
               print("%-28s%-24s%-26s%s" % (response[x]['name'], response[x]['size']/1024/1024/1024, response[x]['host'], response[x]['hgroup']))
         else:
            print "If you're wanting information on specific lun(s) then use the '-v' option"
#
   elif function == 'list_hosts':
#     if host_name has been passed then let's just get info about this else do all hosts
      try:
         host_name
      except:
         response=array.list_hosts(all=True)
      else:
         response=array.list_hosts(names=host_name, all=True)
      if verbose:
         print("%-16s%-26s%-26s%-28s" % ("Name", "WWN", "Host Group", "Presented LUN Name"))
         for x in range(len(response)):
               print("%-16s%-26s%-26s%-28s" % (response[x]['name'], response[x]['host_wwn'], response[x]['hgroup'], response[x]['vol']))
#              response[x]['name']=""
#              response[x]['hgroup']=""
      else:
         response=array.list_hosts()
         for x in range(len(response)):
            print("%-16s%-26s" % (response[x]['name'], response[x]['hgroup']))
###            print response[x]['name']

#
   elif function == 'list_hostgroups':
      response=array.list_hgroups()
      if verbose:
         print("%-28s%-26s" % ("Name", "Hosts"))
         for x in range(len(response)):
            for y in range(len(response[x]['hosts'])):
               print("%-28s%s" % (response[x]['name'], response[x]['hosts'][y]))
               response[x]['name']=""
      else:
         for x in range(len(response)):
            print response[x]['name']
# 
   elif function == 'create_lun':
      try:
         response=array.create_volume(lun_name, lun_size)
         if verbose:
            print("%-28s%-24s%-26s%s" % ("Name", "Size in GB", "Created", "Serial"))
            print("%-28s%-24s%-26s%s" % (response['name'], response['size']/1024/1024/1024, response['created'], response['serial']))
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "LUN Creation failed: {}: {}".format(lun_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'create_host':
      try:
         response=array.create_host(host_name)
         if verbose:
            print "host creation succeeded: {}".format(host_name)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "host creation failed: {}: {}".format(host_name, y[0]['msg'])
         sys.exit(1)
      try:
         wwn_list=wwn_list.split(',')
         response=array.set_host(host_name, wwnlist=wwn_list)
         if verbose:
            print "WWNs added"
            for y in range(len(response['wwn'])):
               print "{}".format(response['wwn'][y])
            sys.exit(0)
      except purestorage.PureHTTPError as response:
         print response
         y=json.loads(response.text)
         print "Failed to allocate WWNs to {}: {}".format(host_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'create_hostgroup':
      try:
         response=array.create_hgroup(group_name)
         if verbose:
            print "hostgroup creation succeeded: {}".format(group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "hostgroup creation failed: {}: {}".format(group_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'add_host_to_hostgroup':
      try:
         host_list=host_name.split(',')
         response=array.set_hgroup(group_name, addhostlist=host_list)
         if verbose:
            print "Succesfully added {} to hostgroup {}".format(host_list, group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Adding {} to hostgroup {} failed: {}".format(host_list, group_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'add_lun_to_hostgroup':
      try:
         response=array.connect_hgroup(group_name, lun_name)
         if verbose:
            print "Succesfully added lun {} to hostgroup {}".format(lun_name, group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Adding lun {} to hostgroup {} failed: {}".format(lun_name, group_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'add_lun_to_host':
      try:
         response=array.connect_host(host_name, lun_name)
         if verbose:
            print "Succesfully added lun {} to host {}: lun={}".format(lun_name, host_name, response['lun'])
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Adding lun {} to host {} failed: {}".format(lun_name, host_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'delete_host':
      try:
         response=array.delete_host(host_name)
         if verbose:
            print "Succesfully deleted host {}".format(host_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Deletion of host {} failed: {}".format(host_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'delete_hostgroup':
      try:
         response=array.delete_hgroup(group_name)
         if verbose:
            print "Succesfully deleted hostgroup {}".format(group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Deletion of hostgroup {} failed: {}".format(group_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'delete_lun':
      try:
         response=array.destroy_volume(lun_name)
         if verbose:
            print "Succesfully deleted volume {}".format(lun_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Deletion of lun {} failed: {}".format(lun_name, y[0]['msg'])
         sys.exit(1)
      try:
         response=array.eradicate_volume(lun_name)
         if verbose:
            print "Succesfully eradicated volume {}".format(lun_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "eradication of lun {} failed: {}".format(lun_name, y[0]['msg'])
         sys.exit(1)
#
   elif function == 'remove_host_from_hostgroup':
      try:
         host_list=host_name.split(',')
         response=array.set_hgroup(group_name, remhostlist=host_list)
         if verbose:
            print "Succesfully removed () from hostgroup {}".format(host_list, group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Removal of hosts {} from hostgroup {} failed: {}".format(host_list, group_name, y[0]['msg'])
         sys.exit(1)
#
###    print '      remove_lun_from_host [ -l | --lun_name ] <lun name> [ -h | --host_name ] <hostname>'
   elif function == 'delete_hostgroup':
      try:
         response=array.delete_hgroup(group_name)
         if verbose:
            print "Succesfully deleted hostgroup {}".format(group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Deletion of hostgroup {} failed: {}".format(group_name, y[0]['msg'])
         sys.exit(1)
#
###    print '      remove_lun_from_hostgroup [ -l | --lun_name ] <lun name> [ -g | --group_name ] <hostgroup_name>'
### disconnect_hgroup(hgroup, volume)

   elif function == 'delete_hostgroup':
      try:
         response=array.delete_hgroup(group_name)
         if verbose:
            print "Succesfully deleted hostgroup {}".format(group_name)
         sys.exit(0)
      except purestorage.PureHTTPError as response:
         y=json.loads(response.text)
         print "Deletion of hostgroup {} failed: {}".format(group_name, y[0]['msg'])
         sys.exit(1)
#

   #disconnect from API
   array.invalidate_cookie()

if __name__ == "__main__":
  main(sys.argv[1:])
