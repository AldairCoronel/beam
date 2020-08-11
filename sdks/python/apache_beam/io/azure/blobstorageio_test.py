#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Tests for Azure Blob Storage client."""
# pytype: skip-file

from __future__ import absolute_import

import logging
import unittest

from apache_beam.io.azure import blobstorageio


class TestAZFSPathParser(unittest.TestCase):

  BAD_AZFS_PATHS = [
    'azfs://'
    'azfs://storage-account/'
    'azfs://storage-account/**'
    'azfs://storage-account/**/*'
    'azfs://container'
    'azfs:///name'
    'azfs:///'
    'azfs:/blah/container/name'
    'azfs://ab/container/name'
    'azfs://accountwithmorethan24chars/container/name'
    'azfs://***/container/name'
    'azfs://storageaccount/my--container/name'
    'azfs://storageaccount/CONTAINER/name'
    'azfs://storageaccount/ct/name'
  ]


  def test_azfs_path(self):
    self.assertEqual(
      blobstorageio.parse_azfs_path('azfs://storageaccount/container/name'), ('storageaccount', 'container', 'name'))
    self.assertEqual(
      blobstorageio.parse_azfs_path('azfs://storageaccount/container/name/sub'), ('storageaccount', 'container', 'name/sub'))

  def test_bad_azfs_path(self):
    for path in self.BAD_AZFS_PATHS:
      self.assertRaises(ValueError, blobstorageio.parse_azfs_path, path)
    self.assertRaises(ValueError, blobstorageio.parse_azfs_path, 'azfs://storageaccount/container/')

  def test_azfs_path_blob_optional(self):
    self.assertEqual(
        blobstorageio.parse_azfs_path('azfs://storageaccount/container/name', blob_optional=True),
        ('storageaccount', 'container', 'name'))
    self.assertEqual(
        blobstorageio.parse_azfs_path('azfs://storageaccount/container/', blob_optional=True),
        ('storageaccount', 'container', ''))

  def test_bad_gcs_path_blob_optional(self):
    for path in self.BAD_AZFS_PATHS:
      self.assertRaises(ValueError, blobstorageio.parse_azfs_path, path, True)

class TestBlobStorageIO(unittest.TestCase):


  def setUp(self):
    self.azfs = blobstorageio.BlobStorageIO()
    self.TEST_DATA_PATH = 'azfs://gsoc2020/gsoc/'

  
  def test_list_prefix(self):

    test_cases = [
        (
            self.TEST_DATA_PATH + 's',
            [
                ('sloth/pictures/sleeping', 2),
                ('sloth/videos/smiling', 3),
                ('sloth/institute/costarica', 5),
            ]),
        (
            self.TEST_DATA_PATH + 'sloth/',
            [
                ('sloth/pictures/sleeping', 2),
                ('sloth/videos/smiling', 3),
                ('sloth/institute/costarica', 5),
            ]),
        (
            self.TEST_DATA_PATH + 'sloth/videos/smiling',
            [
                ('sloth/videos/smiling', 3),
            ]),
    ]

    for file_pattern, expected_object_names in test_cases:
      expected_file_names = [(self.TEST_DATA_PATH + object_name, size)
                             for (object_name, size) in expected_object_names]
      self.assertEqual(
          set(self.azfs.list_prefix(file_pattern).items()),
          set(expected_file_names))
    
if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  unittest.main()
