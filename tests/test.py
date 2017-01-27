import os.path
import tempfile
import unittest
import urllib
import zipfile

import shutil
from aws_tools.s3_handler import S3Handler


class MainTest(unittest.TestCase):

    def setUp(self):
        self.cdn_bucket = "cdn_bucket"
        self.cdn_file = "cdn_file"
        self.out_dir = ''
        self.temp_dir = ''

    def tearDown(self):
        """
        Runs after each test
        """
        # delete temp files
        if os.path.isdir(self.out_dir):
            shutil.rmtree(self.out_dir, ignore_errors=True)
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def testCopy(self):
        user = "photonomad0"
        repo = "aab_obs_text_obs"
        commit = "501f51ba4a"
        bucket = "https://cdn.door43.org"

        self.temp_dir = tempfile.mkdtemp(prefix='downloads_')
        destinationFolder = self.temp_dir

        error, file_names, destinationPaths = self.copyConvertedObsUrlsFromFile(bucket, commit, destinationFolder, repo, user)

        self.assertFalse(error)
        self.assertTrue(os.path.isdir(self.temp_dir))

        for file_name in file_names:
            self.assertTrue(os.path.exists(os.path.join(self.temp_dir, file_name)))

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


if __name__ == "__main__":
    unittest.main()
