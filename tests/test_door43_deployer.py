import codecs
import json
import unittest
import os.path
import tempfile
import urllib

import shutil
from glob import glob

from bs4 import BeautifulSoup
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

    def testCommitToDoor43Complete(self):
        # given
        test_folder_name = "aab_obs_text_obs"
        expect_success = True

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer)


    def testCommitToDoor43MissingChapter01(self):
        # given
        test_folder_name = "aai_obs_text_obs-missing_chapter_01"
        expect_success = True
        missing_chapters = [1]

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer, missing_chapters)


    def testCommitToDoor43Complete_OldConverter(self):
        # given
        test_folder_name = "aab_obs_text_obs-complete_old"
        expect_success = True

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer)


    def testCommitToDoor43Empty_OldConverter(self):
        # given
        test_folder_name = "aae_obs_text_obs-empty_old"
        expect_success = True
        missing_chapters = range(1, 51)

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer, missing_chapters)


    def testCommitToDoor43MissingFirstFrame_OldConverter(self):
        # given
        test_folder_name = "aah_obs_text_obs-missing_first_frame_old"
        expect_success = True

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer)


    def testCommitToDoor43MissingChapter50_OldConverter(self):
        # given
        test_folder_name = "aai_obs_text_obs-missing_chapter_50_old"
        expect_success = True
        missing_chapters = [50]

        # when
        deployer, success = self.doCommitToDoor43(test_folder_name)

        # then
        self.verifyDoor43Deploy(success, expect_success, deployer, missing_chapters)


    # empty
    # <div class="col-md-3 sidebar" id="left-sidebar" role="complementary"><span><select id="page-nav" onchange="window.location.href=this.value"><option value="all.html">all</option></select><div><h1>Revisions</h1><table id="revisions" width="100%"></table></div></span></div>

    # <div class="col-md-3 sidebar" id="left-sidebar" role="complementary"><span><select id="page-nav" onchange="window.location.href=this.value"><option value="01.html">01</option><option value="02.html">02</option><option value="03.html">03</option><option value="04.html">04</option><option value="05.html">05</option><option value="06.html">06</option><option value="07.html">07</option><option value="08.html">08</option><option value="09.html">09</option><option value="10.html">10</option><option value="11.html">11</option><option value="12.html">12</option><option value="13.html">13</option><option value="14.html">14</option><option value="15.html">15</option><option value="16.html">16</option><option value="17.html">17</option><option value="18.html">18</option><option value="19.html">19</option><option value="20.html">20</option><option value="21.html">21</option><option value="22.html">22</option><option value="23.html">23</option><option value="24.html">24</option><option value="25.html">25</option><option value="26.html">26</option><option value="27.html">27</option><option value="28.html">28</option><option value="29.html">29</option><option value="30.html">30</option><option value="31.html">31</option><option value="32.html">32</option><option value="33.html">33</option><option value="34.html">34</option><option value="35.html">35</option><option value="36.html">36</option><option value="37.html">37</option><option value="38.html">38</option><option value="39.html">39</option><option value="40.html">40</option><option value="41.html">41</option><option value="42.html">42</option><option value="43.html">43</option><option value="44.html">44</option><option value="45.html">45</option><option value="46.html">46</option><option value="47.html">47</option><option value="48.html">48</option><option value="49.html">49</option><option value="all.html">all</option><option value="front.html">front</option><option value="hide.50.html">hide.50</option></select><div><h1>Revisions</h1><table id="revisions" width="100%"></table></div></span></div>

    def doCommitToDoor43(self, test_folder_name):
        self.source_dir = os.path.join(self.resources_dir, test_folder_name)
        success = True
        deployer = Door43Deployer(None, None)
        # add mocking for testing
        deployer.door43_handler = MockDoor43Handler(self.resources_dir)
        deployer.cdn_handler = MockCdnHandler(self.source_dir)
        try:
            success = deployer.deploy_commit_to_door43(None)
        except Exception as e:
            print("Door43Deployer threw exception: ")
            print(e)
            success = False

        # get temp folders for later cleanup
        self.out_dir = deployer.output_dir
        self.temp_dir = deployer.template_dir
        self.sources_dir = deployer.source_dir
        return deployer, success

    def verifyDoor43Deploy(self, success, expect_success, deployer, missing_chapters = []):
        self.assertIsNotNone(deployer)
        self.assertIsNotNone(deployer.output_dir)
        self.assertEqual(success, expect_success)

        files_to_verify = []
        files_missing = []
        for i in range(1, 51):
            file_name = str(i).zfill(2) + '.html'
            if not i in missing_chapters:
                files_to_verify.append(file_name)
            else:
                files_missing.append(file_name)

        for file_to_verify in files_to_verify:
            file_path = os.path.join(deployer.output_dir, file_to_verify)
            output_contents = self.getGeneratedContents(file_path)
            self.assertIsNotNone(output_contents, 'OBS HTML body contents not found: {0}'.format(os.path.basename(file_path)))
            file_path2 = os.path.join(self.source_dir, file_to_verify)
            source_contents = self.getContents(file_path2)
            self.assertEqual(source_contents, output_contents, 'OBS HTML source and body contents miscompare: {0}'.format(os.path.basename(file_path)))

        for file_to_verify in files_missing:
            file_path = os.path.join(deployer.output_dir, file_to_verify)
            output_contents = self.getGeneratedContents(file_path)
            self.assertIsNone(output_contents, 'OBS HTML body contents present, but should not be: {0}'.format(os.path.basename(file_path)))

        files_to_verify = []
        files_to_verify.append("build_log.json")
        files_to_verify.append("manifest.json")

        for file_to_verify in files_to_verify:
            file_path = os.path.join(deployer.output_dir, file_to_verify)
            self.assertTrue(os.path.isfile(file_path), 'file not found: {0}'.format(file_path))


    def getGeneratedContents(self, file_path):
        content = self.getContents(file_path)
        if not content:
            return None

        sub_content = content.find(id='content')
        if not sub_content:
            return None

        return sub_content


    def getContents(self, file_path):
        if not os.path.isfile(file_path):
            return None

        with codecs.open(file_path, 'r', 'utf-8-sig') as f:
            soup = BeautifulSoup(f, 'html.parser')

        body = soup.find('body')
        if not body:
            return None

        content = body.find(id='content')
        if not content:
            return None

        return content


    ### used to load test data files:

# def testACopy(self):
#     user = "photonomad0"
#     # repo = "aab_obs_text_obs"
#     # commit = "501f51ba4a"
#     # repo = "aai_obs_text_obs"
#     # commit = "e3f76d2731"
#     repo = "aah_obs_text_obs"
#     commit = "f1fdbae5b7"
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
