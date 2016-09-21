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
    obs_template_url = 'https://s3-us-west-2.amazonaws.com/test-door43.org/templates/obs-rich.html'

    user, repo, commit = job['identifier'].split('/') # identifier = user/repo/commit

    # merge the source files with the template
    with OBSDoor43(source_location_url, output_directory, obs_template_url, False) as merger:
        merger.run()

    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(job['door43_bucket'])
    s3_commit_key = 'u/{0}/{1}/{2}'.format(user, repo, commit)
    s3_project_key = 'u/{0}/{1}'.format(user, repo)

    mime = MimeTypes()
    for root, dirs, files in os.walk(output_directory):
        for f in sorted(files):
            path = os.path.join(root, f)
            key = s3_commit_key + path.replace(output_directory, '')
            mime_type = mime.guess_type(path)[0]
            if not mime_type:
                mime_type = "text/{0}".format(os.path.splitext(path)[1])
            print('Uploading {0} to {1}, mime_type: {2}'.format(f, key, mime_type))
            bucket.upload_file(path, key, ExtraArgs={'ContentType': mime_type})

    try:
        s3_resource.Object(job['door43_bucket'], '{0}/build_log.json'.format(s3_commit_key)).copy_from(CopySource='{0}/{1}/build_log.json'.format(job['cdn_bucket'], s3_commit_key))
        s3_resource.Object(job['door43_bucket'], '{0}/project.json'.format(s3_project_key)).copy_from(CopySource='{0}/{1}/project.json'.format(job['cdn_bucket'], s3_project_key))
        s3_resource.Object(job['door43_bucket'], '{0}/manifest.json'.format(s3_commit_key)).copy_from(CopySource='{0}/{1}/manifest.json'.format(job['cdn_bucket'], s3_commit_key))
        s3_resource.Object(job['door43_bucket'], '{0}/manifest.json'.format(s3_project_key)).copy_from(CopySource='{0}/{1}/manifest.json'.format(job['cdn_bucket'], s3_commit_key))
    except Exception:
        pass

    return True


def redeploy_all_projects(from_bucket, to_bucket):
    return True


def handle(event, context):
    success = False

    if 'Records' in event:
        for record in event['Records']:
            # See if it is a notification from an S3 bucket
            if 's3' in record:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                # if the key ends with a .html, it was a change in template, and so all projects need to be redeployed
                if bucket == door43_bucket and key.endswith('.html'):
                    cdn_bucket = 'cdn.door43.org'
                    door43_bucket = 'door43.org'
                    if bucket.startswith('test-'):
                        cdn_bucket = 'test-'+cdn_bucket
                        door43_bucket = 'test-'+door43_bucket
                        success = redeploy_all_projects(cdn_bucket, door43_bucket)
    elif 'data' in event:
        data = event['data']
        if 'vars' in event and isinstance(event['vars'], dict):
            data.update(event['vars'])
        success = deploy_to_door43(event['data'])

    return {
        'success': success
    }
