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
import os

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

  def test_bad_azfs_path_blob_optional(self):
    for path in self.BAD_AZFS_PATHS:
      self.assertRaises(ValueError, blobstorageio.parse_azfs_path, path, True)

class TestBlobStorageIO(unittest.TestCase):


  def setUp(self):
    self.azfs = blobstorageio.BlobStorageIO()
    self.TEST_DATA_PATH = 'azfs://gsoc2020/gsoc/'

  def test_file_mode(self):
    file_name = self.TEST_DATA_PATH + 'sloth/pictures/sleeping'
    with self.azfs.open(file_name, 'w') as f:
      assert f.mode == 'w'
    with self.azfs.open(file_name, 'r') as f:
      assert f.mode == 'r'

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

  def test_copy(self):
    src_file_name = self.TEST_DATA_PATH + 'mysource'
    dest_file_name = self.TEST_DATA_PATH + 'mydest'
    
    # TODO : add insert_random_file functionality
    
    self.assertTrue(src_file_name in self.azfs.list_prefix(self.TEST_DATA_PATH))
    self.assertFalse(dest_file_name in self.azfs.list_prefix(self.TEST_DATA_PATH))

    self.azfs.copy(src_file_name, dest_file_name)

    self.assertTrue(src_file_name in self.azfs.list_prefix(self.TEST_DATA_PATH))
    self.assertTrue(dest_file_name in self.azfs.list_prefix(self.TEST_DATA_PATH))

    
    # Test copy of non-existent files.
    # with self.assertRaisesRegex(ValueError, 'Blob not found'):
    #   self.azfs.copy(
    #       self.TEST_DATA_PATH + 'non-existent',
    #       self.TEST_DATA_PATH + 'non-existent-destination')

  def test_delete(self):
    file_name = self.TEST_DATA_PATH + 'test_file'
    
    # # Test deletion of non-existent file.
    # self.azfs.delete(file_name) 

    # TODO : add insert_random_file functionality

    files = self.azfs.list_prefix(self.TEST_DATA_PATH)
    self.assertTrue(file_name in files)

    self.azfs.delete(file_name)
    files = self.azfs.list_prefix(self.TEST_DATA_PATH)
    self.assertFalse(file_name in files)
    # TODO : use exists instead

  def test_delete_batch(self):
    file_name_pattern = self.TEST_DATA_PATH + 'delete_batch/%d'
    file_size = 1024
    num_files = 5

    # Test deletion of non-existent files.
    result = self.azfs.delete_batch(
        [file_name_pattern % i for i in range(num_files)])
    self.assertTrue(result)
    for i, (file_name, exception) in enumerate(result):
      self.assertEqual(file_name, file_name_pattern % i)
      self.assertEqual(exception, None)
      self.assertFalse(self.azfs.exists(file_name_pattern % i))

    # Insert some files.
    for i in range(num_files):
      self._insert_random_file(self.client, file_name_pattern % i, file_size)

    # Check files inserted properly.
    for i in range(num_files):
      self.assertTrue(self.azfs.exists(file_name_pattern % i))

    # Execute batch delete.
    self.azfs.delete_batch([file_name_pattern % i for i in range(num_files)])

    # Check files deleted properly.
    for i in range(num_files):
      self.assertFalse(self.azfs.exists(file_name_pattern % i))

  def test_exists(self):
    file_name = self.TEST_DATA_PATH + 'test_file'

    # TODO : add insert_random_file functionality
    
    self.assertFalse(self.azfs.exists(file_name + 'xyz'))
    self.assertTrue(self.azfs.exists(file_name))

  def test_full_file_read(self):
    file_name = self.TEST_DATA_PATH + 'test_file_read'
    file_size = 22
    # TODO : add insert_random_file functionality

    contents = b'Hi beam, how are you?\n'

    f = self.azfs.open(file_name)
    self.assertEqual(f.mode, 'r')
    f.seek(0, os.SEEK_END)
    self.assertEqual(f.tell(), file_size)
    self.assertEqual(f.read(), b'')
    f.seek(0)
    self.assertEqual(f.read(), contents)

    # Clean up
    self.azfs.delete(file_name)

  def test_file_write(self):
    file_name = self.TEST_DATA_PATH + 'test_file_write'
    file_size = 8 * 1024 * 1024 + 2000
    contents = os.urandom(file_size)
    f = self.azfs.open(file_name, 'w')
    self.assertEqual(f.mode, 'w')
    f.write(contents[0:1000])
    f.write(contents[1000:1024 * 1024])
    f.write(contents[1024 * 1024:])
    f.close()
    new_file = self.azfs.open(file_name, 'r')
    new_file_contents = new_file.read()
    self.assertEqual(new_file_contents, contents)

    # Clean up
    self.azfs.delete(file_name)

if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  unittest.main()
