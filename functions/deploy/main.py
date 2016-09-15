# Method for deploying project commits to door43 revision pages

from __future__ import print_function
from __future__ import unicode_literals

import boto3
import tempfile
import os
import json

from datetime import datetime
from mimetypes import MimeTypes
from obs_door43.obs_door43 import OBSDoor43


def deploy_to_door43(job):
    # location of output files that have been converted
    source_location_url = 'https://{0}/u/{1}'.format(job['cdn_bucket'], job['identifier'])
    # where the files should be written after being merged into the template - /tmp/obs
    output_directory = os.path.join(tempfile.gettempdir(), 'obs')
    # the url of the obs template
    obs_template_url = 'https://dev.door43.org/templates/obs.html'

    # merge the source files with the template
    with OBSDoor43(source_location_url, output_directory, obs_template_url, False) as merger:
        merger.run()

    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(job['door43_bucket'])
    s3_project_key = 'u/{0}'.format(job['identifier'])  # identifier = <user>/<repo>/<commit>

    mime = MimeTypes()
    for root, dirs, files in os.walk(output_directory):
        for f in sorted(files):
            path = os.path.join(root, f)
            key = s3_project_key + path.replace(output_directory, '')
            mime_type = mime.guess_type(path)[0]
            if not mime_type:
                mime_type = "text/{0}".format(os.path.splitext(path)[1])
            print('Uploading {0} to {1}, mime_type: {2}'.format(f, key, mime_type))
            bucket.upload_file(path, key, ExtraArgs={'ContentType': mime_type})

    s3_resource.Object(job['door43_bucket'], 'build_log.json').copy_from(CopySource='{0}/u/{1}/build_log.json'.format(job['cdn_bucket'], job['identifier']))
    return True


def handle(event, context):
    deployed = 0
    if 'Records' in event:
        for record in event['Records']:
            if record['eventName'] == 'MODIFY' and 'job_id' in record['dynamodb']['Keys']:
                print("DynamoDB Record: " + json.dumps(record['dynamodb'], indent=2))
                job_id = record['dynamodb']['Keys']['job_id']['S']
                print("job_id: {}".format(job_id))
                job_table = boto3.resource('dynamodb').Table('tx-job')
                response = job_table.get_item(
                    Key={
                        'job_id': job_id
                    }
                )
                if 'Item' in response:
                    job = response['Item']
                    print("JOB:")
                    print(job)
                    if 'success' in job and job['success'] and ('deployed' not in job or not job['deployed']):
                        success = deploy_to_door43(job)
                        if success:
                            deployed_at_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                            job_table.update_item(
                                Key={
                                   'job_id': job['job_id'],
                                },
                                UpdateExpression="set deployed_at = :deployed_at, deployed = :deployed",
                                ExpressionAttributeValues={
                                    ':deployed_at': deployed_at_timestamp,
                                    ':deployed': True
                                }
                            )
                            deployed += 1
        return {
            'success': True,
            'message': 'Successfully deployed {} job(s).'.format(deployed)
        }
