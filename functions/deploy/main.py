# Method for deploying project commits to door43 revision pages

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import tempfile
import json
import boto3

import templaters

from datetime import datetime
from mimetypes import MimeTypes

from general_tools.url_utils import get_url
from general_tools.file_utils import write_file
from aws_tools.s3_handler import S3Handler


def str_to_class(str):
    return reduce(getattr, str.split("."), sys.modules[__name__])


def deploy_to_door43(job):
    source_dir = tempfile.mkdtemp(prefix='source_')
    output_dir = tempfile.mkdtemp(prefix='output_')
    template_dir = tempfile.mkdtemp(prefix='template_')

    s3 = S3Handler()
    s3.download_dir(job['cdn_bucket'], 'u/'+job['identifier'], source_dir)
    source_dir = os.path.join(source_dir, 'u/'+job['identifier'])

    # determining the template and templater from the resource_type, use general if not found
    try:
        templater_class = str_to_class('templaters.{0}Templater'.format(job['resource_type'].capitalize()))
        template_url = '{0}/templates/{1}.html'.format(job['door43_url'], job['resource_type'])
    except AttributeError:
        templater_class = templaters.Templater
        template_url = '{0}/templates/{1}.html'.format(job['door43_url'], 'obs')

    template_file = os.path.join(template_dir, 'template.html')
    print("Downloading {0}...".format(template_url))
    write_file(template_file, get_url(template_url))

    # merge the source files with the template
    templater = templater_class(source_dir, output_dir, template_file)
    templater.run()

    user, repo, commit = job['identifier'].split('/')  # identifier = user/repo/commit

    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(job['door43_bucket'])
    s3_commit_key = 'u/{0}/{1}/{2}'.format(user, repo, commit)
    s3_project_key = 'u/{0}/{1}'.format(user, repo)

    mime = MimeTypes()
    for root, dirs, files in os.walk(output_dir):
        for f in sorted(files):
            path = os.path.join(root, f)
            key = s3_commit_key + path.replace(output_dir, '')
            mime_type = mime.guess_type(path)[0]
            if not mime_type:
                mime_type = "text/{0}".format(os.path.splitext(path)[1])
            print('Uploading {0} to {1}, mime_type: {2}'.format(f, key, mime_type))
            bucket.upload_file(path, key, ExtraArgs={'ContentType': mime_type, 'CacheControl': 'max-age=0'})

    try:
        s3_resource.Object(job['door43_bucket'], '{0}/index.html'.format(s3_commit_key)).copy_from(CopySource='{0}/{1}/01.html'.format(job['door43_bucket'], s3_commit_key))
        s3_resource.Object(job['door43_bucket'], '{0}/build_log.json'.format(s3_commit_key)).copy_from(CopySource='{0}/{1}/build_log.json'.format(job['cdn_bucket'], s3_commit_key))
        s3_resource.Object(job['door43_bucket'], '{0}/project.json'.format(s3_project_key)).copy_from(CopySource='{0}/{1}/project.json'.format(job['cdn_bucket'], s3_project_key))
        s3_resource.Object(job['door43_bucket'], '{0}/manifest.json'.format(s3_commit_key)).copy_from(CopySource='{0}/{1}/manifest.json'.format(job['cdn_bucket'], s3_commit_key))
        s3_resource.Object(job['door43_bucket'], '{0}/manifest.json'.format(s3_project_key)).copy_from(CopySource='{0}/{1}/manifest.json'.format(job['cdn_bucket'], s3_commit_key))

        # Download the project.json and generate temp index.html page
        try:
            s3_repo_key = 'u/{0}/{1}'.format(user, repo)
            project_url = '{0}/{1}/project.json'.format(job['cdn_url'], s3_repo_key)
            print("Getting {0}...".format(project_url))
            project = json.loads(get_url(project_url))
            print("GOT:")
            print(project)

            html = '<html><head><title>{0}</title></head><body><h1>{0}</h1><ul>'.format(repo)
            for commit in project['commits']:
                html += '<li><a href="{0}/01.html">{0}</a> - {1}</li>'.format(commit['id'], commit['created_at'])
            html += '</ul></body></html>'
            repo_index_file = os.path.join(tempfile.gettempdir(), 'index.html')
            write_file(repo_index_file, html)
            bucket.upload_file(repo_index_file, s3_repo_key + '/index.html',
                               ExtraArgs={'ContentType': 'text/html', 'CacheControl': 'max-age=0'})
        except Exception as e:
            print("FAILED: {0}".format(e.message))
        finally:
            print('finished.')

    except Exception:
        pass

    return True


def redeploy_all_projects(from_bucket, to_bucket):
    # Todo: Template changed, so we need to redeploy all commit pages
    return True


def handle(event, context):
    success = False

    # If we got 'Records' that means a template change was upoaded to S3 and we got the trigger
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
    # Else this function was called with 'data' to deploy a single commit
    elif 'data' in event:
        data = event['data']
        if 'vars' in event and isinstance(event['vars'], dict):
            data.update(event['vars'])

        if 'vars' in event and isinstance(event['vars'], dict):
            data.update(event['vars'])
        success = deploy_to_door43(event['data'])

    return {
        'success': success
    }
