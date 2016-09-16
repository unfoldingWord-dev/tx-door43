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
    with OBSD`oor43(source_location_url, output_directory, obs_template_url, False) as merger:
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

def download_dir(client, resource, dist, local='/tmp', bucket='your_bucket'):
    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=dist):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                download_dir(client, resource, subdir.get('Prefix'), local, bucket)
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local + os.sep + file.get('Key'))):
                    os.makedirs(os.path.dirname(local + os.sep + file.get('Key')))
                resource.meta.client.download_file(bucket, file.get('Key'), local + os.sep + file.get('Key'))

def deploy_project(from_bucket, to_bucket, key):
    client = boto3.client('s3')
    resource = boto3.resource('s3')

    tmpdir = tempfile.mkdtemp(prefix=from_bucket)
    download_dir(client, resource, key, tmpdir, from_bucket)

    
    return True


def redeploy_all_projects(from_bucket, to_bucket):
    return True


def handle(event, context):
    success = False
    if 'Records' in event:
        for record in event['Records']:
            # See if it is a notification from an S3 bucket
            if "s3" in record:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']

                cdn_bucket = 'cdn.door43.org'
                door43_bucket = 'door43.org'
                if bucket.startswith('test-'):
                    cdn_bucket = 'test-'+cdn_bucket
                    door43_bucket = 'test-'+door43_bucket

                # if the key ends with a .html, it was a change in template, and so all projects need to be redeployed
                if bucket == door43_bucket and key.endswith('.html'):
                    success = redeploy_all_projects(cdn_bucket, door43_bucket)
                # else if it ends with build_log.json it was a change in the CDN and thus only that project needs to be generated
                elif bucket.endswith('cdn.door43.org') and key.endswith("build_log.json"):
                    sucess = deploy_project(cdn_bucket, door43_bucket, os.path.dirname(key))
        return {
            'success': success,
        }
