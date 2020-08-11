 
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

"""Azure Blob Storage client.
"""

# pytype: skip-file

from __future__ import absolute_import

import io
import logging
import re
import threading
import time
import os
from builtins import object

from apache_beam.io.filesystemio import Downloader
from apache_beam.io.filesystemio import DownloaderStream
from apache_beam.io.filesystemio import Uploader
from apache_beam.io.filesystemio import UploaderStream
from apache_beam.utils import retry

try:
  # pylint: disable=wrong-import-order, wrong-import-position
  # pylint: disable=ungrouped-imports
  from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
except ImportError:
  raise ImportError('Missing `azure` requirement')

DEFAULT_READ_BUFFER_SIZE = 16 * 1024 * 1024

MAX_BATCH_OPERATION_SIZE = 100


def parse_azfs_path(azfs_path, blob_optional=False):
  """Return the storage account, the container and blob names of the given azfs:// path."""
  match = re.match('^azfs://([a-z0-9]{3,24})/([a-z0-9](?![a-z0-9-]*--[a-z0-9-]*)[a-z0-9-]{1,61}[a-z0-9])/(.*)$', azfs_path)
  if match is None or (match.group(3) == '' and not blob_optional):
    raise ValueError('Azure Blob Storage path must be in the form azfs://<storage-account>/<container>/<path>.')
  return match.group(1), match.group(2), match.group(3)


class BlobStorageIOError(IOError, retry.PermanentException):
  """Blob Strorage IO error that should not be retried."""
  pass


class BlobStorageIO(object):
  """Azure Blob Storage I/O client."""

  def __init__(self, client=None):
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if client is None:
      self.client = BlobServiceClient.from_connection_string(connect_str)
    else:
      self.client = client

  def open(
      self,
      filename,
      mode='r',
      read_buffer_size=DEFAULT_READ_BUFFER_SIZE,
      mime_type='application/octet-stream'):
    """Open an Azure Blob Storage file path for reading or writing.
    Args:
      filename (str): Azure Blob Storage file path in the form
      ``azfs://<storage-account>/<container>/<path>``.
      mode (str): ``'r'`` for reading or ``'w'`` for writing.
      read_buffer_size (int): Buffer size to use during read operations.
      mime_type (str): Mime type to set for write operations.
    Returns:
      Azure Blob Storage file object.
    Raises:
      ValueError: Invalid open file mode.
    """
    if mode == 'r' or mode == 'rb':
      downloader = BlobStorageDownloader(
          self.client, filename, buffer_size=read_buffer_size)
      return io.BufferedReader(
          DownloaderStream(
              downloader, read_buffer_size=read_buffer_size, mode=mode),
          buffer_size=read_buffer_size)
    elif mode == 'w' or mode == 'wb':
      uploader = BlobStorageUploader(self.client, filename, mime_type)
      return io.BufferedWriter(
          UploaderStream(uploader, mode=mode), buffer_size=128 * 1024)
    else:
      raise ValueError('Invalid file open mode: %s.' % mode)

  @retry.with_exponential_backoff(
      retry_filter=retry.retry_on_server_errors_and_timeout_filter)
  def list_prefix(self, path):
    """Lists files matching the prefix.

    Args:
      path: Azure Blob Storage file path pattern in the form
            azfs://<storage-account>/<container>/[name].

    Returns:
      Dictionary of file name -> size.
    """
    storage_account, container, blob = parse_azfs_path(path, blob_optional=True)
    file_sizes = {}
    counter = 0
    start_time = time.time()

    logging.info("Starting the size estimation of the input")
    container_client = self.client.get_container_client(container)

    while True:
      response = container_client.list_blobs(name_starts_with=blob)
      for item in response:
        file_name = "azfs://%s/%s/%s" % (storage_account, container, item.name)
        file_sizes[file_name] = item.size
        counter += 1
        if counter % 10000 == 0:
          logging.info("Finished computing size of: %s files", len(file_sizes))
      break

    logging.info(
        "Finished listing %s files in %s seconds.",
        counter,
        time.time() - start_time)
    return file_sizes



  
  
    
