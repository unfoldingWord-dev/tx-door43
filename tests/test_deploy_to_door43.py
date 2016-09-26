import unittest
import os.path

from unittest import TestCase

from functions.deploy.main import deploy_to_door43

class TestDeploy_to_door43(TestCase):
    def test_deploy_to_door43(self):
        deploy_to_door43({
            "input_format": "md",
            "convert_module": "tx-md2html_convert",
            "message": "Conversion successful",
            "started_at": "2016-09-25T15:45:12Z",
            "errors": [],
            "job_id": "496a4e3f2492d2fa08a8674469369945723dece8d141e8e959520b14f1f625da",
            "output_expiration": None,
            "links": {
                "href": "https://test-api.door43.org/tx/job/496a4e3f2492d2fa08a8674469369945723dece8d141e8e959520b14f1f625da",
                "method": "GET",
                "rel": "self"
            },
            "source": "https://s3-us-west-2.amazonaws.com/test-tx-webhook/tx-webhook-client/0b03156f-8337-11e6-8526-a3446f42ae41.zip",
            "status": "success",
            "warnings": [],
            "output_format": "html",
            "expires_at": "2016-09-26T15:45:12Z",
            "user": "txwebhook",
            "cdn_file": "tx/job/0b4cefab-8337-11e6-b721-af31838aaeb4.zip",
            "cdn_bucket": "test-cdn.door43.org",
            "ended_at": "2016-09-25T15:45:14Z",
            "success": True,
            "created_at": "2016-09-25T15:45:12Z",
            "callback": "https://test-api.door43.org/client/callback",
            "eta": "2016-09-25T15:45:32Z",
            "output": "https://test-cdn.door43.org/tx/job/0b4cefab-8337-11e6-b721-af31838aaeb4.zip",
            "identifier": "d43/en-obs/88e4ef27a8",
            "resource_type": "obs",
            "door43_url": "https://dev.door43.org",
            "cdn_bucket": "test-cdn.door43.org",
            "cdn_url": "https://test-cdn.door43.org",
            "api_url": "https://test-api.door43.org"
        })

if __name__ == "__main__":
    unittest.main()
