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


class Door43Deployer(object):
    def __init__(self, cdn_bucket, door43_bucket):
        self.cdn_bucket = cdn_bucket
        self.door43_bucket = door43_bucket
        self.cdn_handler = S3Handler(cdn_bucket)
        self.door43_handler = S3Handler(door43_bucket)

    def deploy_commit_to_door43(self, build_json_key):
        build_log = cdn_handler.get_json(build_json_key)

        if not build_log or 'commit_id' not in build_log:
            return False

        source_dir = tempfile.mkdtemp(prefix='source_')
        output_dir = tempfile.mkdtemp(prefix='output_')
        template_dir = tempfile.mkdtemp(prefix='template_')

        cdn_handler.download_dir(dir, source_dir)
        source_dir = os.path.join(source_dir, dir)

        # determining the template and templater from the resource_type, use general if not found
        try:
            templater_class = str_to_class('templaters.{0}Templater'.format(build_log['resource_type'].capitalize()))
            template_url = 'https://s3-us-west-2.amazon.com/{0}/templates/{1}.html'.format(door43_bucket,
                                                                                           build_log['resource_type'])
        except AttributeError:
            templater_class = templaters.Templater
            template_url = 'https://s3-us-west-2.amazon.com/{0}/templates/{1}.html'.format(door43_bucket, 'obs')

        template_file = os.path.join(template_dir, 'template.html')
        print("Downloading {0}...".format(template_url))
        write_file(template_file, get_url(template_url))

        # merge the source files with the template
        templater = templater_class(source_dir, output_dir, template_file)
        templater.run()

        user = build_log['repo_owner']
        repo = build_log['repo_name']
        commit = build_log['commit_id'][:10]

        s3_commit_key = 'u/{0}/{1}/{2}'.format(user, repo, commit)
        s3_project_key = 'u/{0}/{1}'.format(user, repo)

        door43_handler.copy(from_key, to_key, from_bucket=None, to_bucket=None)

        # Now we place json files and make an html file
        try:
            door43_handler.copy(from_key='{0}/build_log.json'.format(s3_commit_key), from_bucket=self.cdn_bucket)
            door43_handler.copy(from_key='{0}/project.json'.format(s3_project_key), from_bucket=self.cdn_bucket)
            door43_handler.copy(from_key='{0}/manifest.json'.format(s3_commit_key), from_bucket=self.cdn_bucket)
            door43_handler.copy(from_key='{0}/manifest.json'.format(s3_commit_key), from_bucket=self.cdn_bucket,
                                to_key='{0}/manifest.json'.format(s3_project_key))

            # Download the project.json and generate repo's index.html page
            try:
                project_json_key = '{0}/{1}/{2}/project.json'.format(build_log['cdn_url'], user, repo)
                print("Getting {0}...".format(project_json_key))
                project_json = self.cdn_handler.get_json(project_json_key)

                html = '<html><head><title>{0}</title></head><body><h1>{0}</h1><ul>'.format(repo)
                for commit in project_json['commits']:
                    html += '<li><a href="{0}/01.html">{0}</a> - {1}</li>'.format(commit['id'], commit['created_at'])
                html += '</ul></body></html>'
                repo_index_file = os.path.join(tempfile.gettempdir(), 'index.html')
                write_file(repo_index_file, html)
                door43_handler.upload_file(repo_index_file, s3_repo_key + '/index.html', 0)
            except Exception as e:
                print("FAILED: {0}".format(e.message))
            finally:
                print('finished.')

        except Exception:
            pass

        return True

    def redeploy_all_commits(self):
        success = True
        for obj in self.cdn_handler.get_objects(prefix='u/', suffix='build_log.json'):
            success = (success and self.deploy_commit_to_door43(obj.key))
        return success


def handle(event, context):
    success = False
    # If we got 'Records' that means a template change was upoaded to S3 and we got the trigger
    if 'Records' in event:
        for record in event['Records']:
            # See if it is a notification from an S3 bucket
            if 's3' in record:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']

                cdn_bucket = 'cdn.door43.org'
                door43_bucket = 'door43.org'
                if bucket.startswith('test-'):
                    cdn_bucket = 'test-'+door43_bucket
                    door43_bucket = 'test-'+door43_bucket

                # if the key ends with a .html, it was a change in template, and so all projects need to be redeployed
                if key.endswith('.html'):
                    success = Door43Deployer(cdn_bucket, door43_bucket).redeploy_all_commits()
                elif key.endswith('build_log.json'):
                    success = Door43Deployer(cdn_bucket, door43_bucket).deploy_commit_to_door43(key)

    return {
        'success': success
    }
