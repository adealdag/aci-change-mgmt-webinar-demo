import logging
import sys

from cobra.mit.access import MoDirectory
from cobra.mit.session import LoginSession
from cobra.mit.request import *

# Credentials, complete with the required information
apic_url = "https://" + os.getenv('APIC_HOST')
apic_user = os.getenv('APIC_USERNAME')
apic_pwd = os.getenv('APIC_PASSWORD')

# Set logging
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

# Get tenant to lookup
logging.debug("Function argument is " + sys.argv[1])
my_tenant_to_lookup = sys.argv[1]
total_tenant_fauls = 0

# Logging into APIC
session = LoginSession(apic_url, apic_user, apic_pwd)
moDir = MoDirectory(session)
moDir.login()

logging.debug('Logging into APIC Successful')

# Fetch all the faults
faults = moDir.lookupByClass('faultInst')

# Create a list where the faults will go
fault_tab = []

# Parse the faults to add in the list
for fault in faults:
    dn = str(fault.dn)
    split_dn = dn.split("/")
    if dn.startswith("uni/tn-"):
        fault_tab.append({"tenant": split_dn[1][3:],
                          "date": fault.created,
                          "cause": fault.cause,
                          "description": fault.descr})

# Print faults and return
logging.debug("List of faults in tenant " + my_tenant_to_lookup)
for fault in fault_tab:
    if fault["tenant"] == my_tenant_to_lookup:
        logging.debug(fault)
        total_tenant_fauls += 1

logging.debug("Total faults: " + str(total_tenant_fauls))

sys.exit(total_tenant_fauls)
