import logging
import sys
import requests
import json
import time
import os
import argparse

# Credentials and login details must be provided as env variables
nd_url = "https://" + os.getenv('ND_HOST')
nd_user = os.getenv('ND_USERNAME')
nd_pwd = os.getenv('ND_PASSWORD')
nd_domain = os.getenv('ND_DOMAIN')


# Set argument parser
parser = argparse.ArgumentParser(
    description="Run a Pre-Change Analysis on Nexus Dashboard Insights using a file that contains the configuration changes. The base epoch is the latest one available.")
parser.add_argument(
    "--name", help="pre-change analysis name (required)", required=True)
parser.add_argument(
    "--descr", help="pre-change analysis description (optional)", default="")
parser.add_argument(
    "--igname", help="insights group name (required)", required=True)
parser.add_argument(
    "--site", help="site or fabric name (required)", required=True)
parser.add_argument(
    "--file", help="change definition file path (required)", required=True)
parser.add_argument(
    "--timeout", help="pre-change analysis timeout, in minutes (optional, default is 15)", type=int, default=15)
parser.add_argument(
    "--loglevel", help="logging level (optional, default is WARNING)", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"])

args = parser.parse_args()

# Set logging
rootLogger = logging.getLogger()
rootLogger.setLevel(args.loglevel)

# Create session
session = requests.Session()
session.verify = False

# Login into nd
url = nd_url + "/login"

payload = json.dumps({
    "userName": nd_user,
    "userPasswd": nd_pwd,
    "domain": nd_domain
})
headers = {
    'Content-Type': 'application/json'
}

response = session.post(url, headers=headers, data=payload)

if response.status_code != 200:
    logging.error("Authentication failed: {}".format(response.json()))
    sys.exit(-1)
else:
    logging.info("Authentication succeeded for user {}".format(nd_user))


# Get base epoch information
url = nd_url + \
    "/sedgeapi/v1/cisco-nir/api/api/telemetry/v2/events/insightsGroup/{}/fabric/{}/epochs?$size=1&$status=FINISHED".format(
        args.igname, args.site)

response = session.get(url, headers={})

if response.status_code != 200:
    logging.error("Base Epoch collection failed: {}".format(
        response.json()))
    sys.exit(-1)
else:
    base_epoch_data = response.json()["value"]["data"][0]
    logging.info("Selecting latest epoch as base. Base epoch uuid is: " +
                 base_epoch_data["epochId"])


# Create pre-change validation
url = nd_url + \
    "/sedgeapi/v1/cisco-nir/api/api/telemetry/v2/config/insightsGroup/{}/fabric/{}/prechangeAnalysis/fileChanges".format(
        args.igname, args.site)

data = {
    "allowUnsupportedObjectModification": False,
    "analysisSubmissionTime": round(time.time() * 1000),
    "baseEpochId": base_epoch_data["epochId"],
    "baseEpochCollectionTimestamp": base_epoch_data["collectionTimeMsecs"],
    "fabricUuid": base_epoch_data["fabricId"],
    "description": args.descr,
    "name": args.name,
    "assuranceEntityName": args.site,
    "uploadedFileName": args.name
}

with open('data.json', 'wb') as data_file:
    json.dump(data, data_file)

files = [
    ('data', ('data.json', open('data.json', 'rb'), 'application/json')),
    ('file', ('app-hrms.xml', open(args.file, 'rb'), 'text/xml'))
]

response = session.post(
    url, headers={}, data={}, files=files)

if response.status_code != 200:
    logging.error("Pre-change analysis job creation failed: {}".format(
        response.json()))
    sys.exit(-1)
else:
    pcv_job_data = response.json()["value"]["data"]
    logging.info("Pre-change analysis job created. Job id is: " +
                 pcv_job_data["jobId"])

# Get job information - Loop until completed
retries_left = 15  # Retry 15 times, once per minute
job_status = "UNKNOWN"

while(job_status != "COMPLETED" and retries_left > 0):
    time.sleep(60)

    url = nd_url + \
        "/sedgeapi/v1/cisco-nir/api/api/telemetry/v2/config/insightsGroup/{}/fabric/{}/prechangeAnalysis/{}".format(
            args.igname, args.site, pcv_job_data["jobId"])

    response = session.get(url, headers={})

    if response.status_code != 200:
        logging.error("Pre-change analysis job status collection failed: {}".format(
            response.json()))
        sys.exit(-1)
    else:
        pcv_job_status_data = response.json()["value"]["data"]
        logging.debug("Job status is: " +
                      pcv_job_status_data["analysisStatus"])

    job_status = pcv_job_status_data["analysisStatus"]

    if (job_status != "COMPLETED"):
        retries_left -= 1
        logging.info(
            "Job is still not completed, current state is {}. There are {} retries left. Checking again in 60 seconds...".format(job_status, retries_left))
        continue

# Get pre-change analysis epoch information
url = nd_url + \
    "/sedgeapi/v1/cisco-nir/api/api/telemetry/v2/events/insightsGroup/{}/fabric/{}/epochs?$epochId={}".format(
        args.igname, args.site, pcv_job_status_data["preChangeEpochUUID"])

response = session.get(url, headers={})

if response.status_code != 200:
    logging.error("Pre-change Epoch collection failed: {}".format(
        response.json()))
    sys.exit(-1)
else:
    pcv_epoch_data = response.json()["value"]["data"][0]

# Analyze epoch data
assurance_info = pcv_epoch_data["assuranceInfo"]
delta_result = 0

for sev in assurance_info:
    logging.info(
        "There are {} new {} anomalies after pre-change analysis".format(sev["count"], sev["severity"].upper()))
    delta_result += sev["count"]

logging.info("Total number of new anomalies is: {}".format(delta_result))
sys.exit(delta_result)
