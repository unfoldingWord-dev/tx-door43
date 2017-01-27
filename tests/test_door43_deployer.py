import json
import unittest
import os.path
import tempfile
import urllib

import shutil
from glob import glob

from general_tools import file_utils

from functions.deploy import Door43Deployer

class TestDoor43Deployer(unittest.TestCase):

    resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')

    def setUp(self):
        self.cdn_bucket = "cdn_bucket"
        self.cdn_file = "cdn_file"
        self.out_dir = ''
        self.temp_dir = ''
        self.sources_dir = ''

    def tearDown(self):
        """
        Runs after each test
        """
        # delete temp files
        if os.path.isdir(self.out_dir):
            shutil.rmtree(self.out_dir, ignore_errors=True)
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        if os.path.isdir(self.sources_dir):
            shutil.rmtree(self.sources_dir, ignore_errors=True)

    def testCommitToDoor43(self):
        test_folder_name = "aab_obs_text_obs-complete"

        source_dir = os.path.join(self.resources_dir, test_folder_name)
        output_dir = tempfile.mkdtemp(prefix='output_')
        template_dir = tempfile.mkdtemp(prefix='template_')

        success = True
        deployer = Door43Deployer(None, None)
        # add mocking for testing
        deployer.door43_handler = MockDoor43Handler(self.resources_dir)
        deployer.cdn_handler = MockCdnHandler(source_dir)
        try:
            deployer.deploy_commit_to_door43(None)
        except:
            success = False

        # get temp folders for later cleanup
        self.out_dir = deployer.output_dir
        self.temp_dir = deployer.template_dir
        self.sources_dir = deployer.source_dir

        self.assertTrue(success)

        # TODO: need to add some file validation here


    # def testCopy(self):
    #     user = "photonomad0"
    #     # repo = "aab_obs_text_obs"
    #     # commit = "501f51ba4a"
    #     repo = "aai_obs_text_obs"
    #     commit = "e3f76d2731"
    #     bucket = "https://cdn.door43.org"
    #
    #     self.temp_dir = tempfile.mkdtemp(prefix='downloads_')
    #     destinationFolder = self.temp_dir
    #
    #     error, file_names, destinationPaths = self.copyConvertedObsUrlsFromFile(bucket, commit, destinationFolder, repo, user)
    #
    #     self.assertFalse(error)
    #     self.assertTrue(os.path.isdir(self.temp_dir))
    #
    #     for file_name in file_names:
    #         self.assertTrue(os.path.exists(os.path.join(self.temp_dir, file_name)))

    def copyConvertedObsUrlsFromFile(self, bucket, commit, destinationFolder, repo, user):
        source = "%s/u/%s/%s/%s" % (bucket, user, repo, commit)
        file_names = [str(i).zfill(2) + '.html' for i in range(1, 51)]
        file_names.append("build_log.json")
        file_names.append("manifest.json")
        destinationPaths, error = self.copyFilesFromUrl(file_names, source, destinationFolder)
        return error, file_names, destinationPaths

    def copyFilesFromUrl(self, file_names, source, destinationFolder):
        destinationPaths = []
        error = False
        for file_name in file_names:
            print("Downloading :" + file_name)
            destinationPath = self.copyFileFromUrl(file_name, source, destinationFolder)
            if destinationPath:
                destinationPaths.append(destinationPath)
            else:
                print("Could not get: " + file_name)
                error = True

        return destinationPaths, error

    def copyFileFromUrl(self, file_name, source, destinationFolder):
        destinationPath = os.path.join(destinationFolder, file_name)
        source_path = os.path.join(source, file_name)

        try:
            urllib.urlretrieve(source_path, destinationPath)
            return destinationPath

        except Exception:
            print("Could not copy: " + source_path)
            return None


class MockDoor43Handler(object):
    def __init__(self, bucket):
        self.bucket_name = bucket

    def download_file(self, key, local_file):
        source_file = os.path.join(self.bucket_name, key)
        shutil.copyfile(source_file, local_file)

    def upload_file(self, path, key, cache_time=600):
        pass

    def copy(self, from_key, from_bucket=None, to_key=None, catch_exception=True):
        pass

    def redirect(self, key, location):
        pass


class MockCdnHandler(object):
    def __init__(self, bucket):
        self.bucket_name = bucket

    def get_json(self, key):
        source_file = os.path.join(self.bucket_name, 'build_log.json')
        build_log = None
        with open(source_file) as json_data:
            build_log = json.load(json_data)

        return build_log

    def download_dir(self, key_prefix, local):
        output_folder = os.path.join(local, key_prefix)
        file_utils.make_dir(output_folder)
        for filename in sorted(glob(os.path.join(self.bucket_name, '*'))):
            output_file = os.path.join(output_folder, os.path.basename(filename))
            shutil.copyfile(filename, output_file)

if __name__ == '__main__':
    unittest.main()
