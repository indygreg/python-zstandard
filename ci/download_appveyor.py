#!/usr/bin/env python

# Downloads AppVeyor artifacts to the local directory.
#
# This script is a bit hacky. But it gets the job done.

import sys

import requests


def make_request(session, path):
    url = 'https://ci.appveyor.com/api/%s' % path
    return session.get(url)


def download_artifacts(project):
    session = requests.session()

    project_info = make_request(session, 'projects/%s' % project)
    jobs = project_info.json()['build']['jobs']

    for job in jobs:
        print(job['name'])

        if not job['artifactsCount']:
            continue

        artifacts = make_request(session, 'buildjobs/%s/artifacts' % job['jobId'])
        for artifact in artifacts.json():
            print('downloading %s' % artifact['fileName'])
            response = make_request(session, 'buildjobs/%s/artifacts/%s' % (
                job['jobId'], artifact['fileName']))

            if response.status_code != 200:
                continue

            with open(artifact['fileName'], 'wb') as fh:
                for chunk in response.iter_content(8192):
                    fh.write(chunk)


if __name__ == "__main__":
    download_artifacts(sys.argv[1])
