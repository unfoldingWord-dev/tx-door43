# Method for deploying project commits to door43 revision pages

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import tempfile

import templaters

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

    def deploy_commit_to_door43(self, build_log_key):
        build_log = None
        try:
            build_log = self.cdn_handler.get_json(build_log_key)
        except:
            pass

        print(build_log)

        if not build_log or 'commit_id' not in build_log or 'repo_owner' not in build_log or 'repo_name' not in build_log:
            return False

        user = build_log['repo_owner']
        repo_name = build_log['repo_name']
        commit_id = build_log['commit_id'][:10]

        s3_commit_key = 'u/{0}/{1}/{2}'.format(user, repo_name, commit_id)
        s3_project_key = 'u/{0}/{1}'.format(user, repo_name)

        source_dir = tempfile.mkdtemp(prefix='source_')
        output_dir = tempfile.mkdtemp(prefix='output_')
        template_dir = tempfile.mkdtemp(prefix='template_')

        self.cdn_handler.download_dir(s3_commit_key, source_dir)
        source_dir = os.path.join(source_dir, s3_commit_key)

        # determining the template and templater from the resource_type, use general if not found
        try:
            templater_class = str_to_class('templaters.{0}Templater'.format(build_log['resource_type'].capitalize()))
            template_key = 'templates/{1}.html'.format(build_log['resource_type'])
        except AttributeError:
            templater_class = templaters.Templater
            template_key = 'templates/{1}.html'.format('obs')

        template_file = os.path.join(template_dir, 'template.html')
        print("Downloading {0} to {1}...".format(template_key, template_file))
        self.door43_handler.download_file(template_key, template_dir)

        # merge the source files with the template
        templater = templater_class(source_dir, output_dir, template_file)
        templater.run()

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
                project_json_key = '{0}/{1}/{2}/project.json'.format(build_log['cdn_url'], user, repo_name)
                print("Getting {0}...".format(project_json_key))
                project_json = self.cdn_handler.get_json(project_json_key)

                html = '<html><head><title>{0}</title></head><body><h1>{0}</h1><ul>'.format(repo_name)
                for commit_id in project_json['commits']:
                    html += '<li><a href="{0}/01.html">{0}</a> - {1}</li>'.format(commit_id['id'], commit_id['created_at'])
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
            print(record)
            # See if it is a notification from an S3 bucket
            if 's3' in record:
                bucket_name = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                print(bucket_name, key)

                cdn_bucket = 'cdn.door43.org'
                door43_bucket = 'door43.org'
                if bucket_name.startswith('test-'):
                    cdn_bucket = 'test-'+cdn_bucket
                    door43_bucket = 'test-'+door43_bucket
                print(cdn_bucket, door43_bucket)

                # if the key ends with a .html, it was a change in template, and so all projects need to be redeployed
                if key.endswith('.html'):
                    print('.html')
                    success = Door43Deployer(cdn_bucket, door43_bucket).redeploy_all_commits()
                elif key.endswith('build_log.json'):
                    print('.json')
                    success = Door43Deployer(cdn_bucket, door43_bucket).deploy_commit_to_door43(key)

    return {
        'success': success
    }
