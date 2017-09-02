# Copyright (c) 2014-2017, iocage
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted providing that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
import os.path
import json

import libiocage.lib.helpers


def to_json(data: dict):
    output_data = {}
    for key, value in data.items():
        output_data[key] = libiocage.lib.helpers.to_string(
            value,
            true="yes",
            false="no",
            none="none"
        )
    return json.dumps(output_data, sort_keys=True, indent=4)


class ConfigJSON:

    def __init__(
        self,
        file: str,
        logger: libiocage.lib.Logger.Logger
    ):

        libiocage.lib.helpers.init_logger(self, logger)
        self._file = file

    @property
    def file(self):
        return self._file

    def read(self) -> dict:
        try:
            with open(self.file, "r") as conf:
                return json.load(conf)
        except:
            return {}

    def write(self, data: dict):
        """
        Writes changes to the config file
        """
        with open(self.file, "w") as conf:
            conf.write(to_json(data))
            conf.truncate()


class ResourceConfigJSON:

    def __init__(
        self,
        resource: libiocage.lib.Resource.Resource,
        **kwargs
    ):

        self.resource = resource
        JailConfigFile.__init__(self, **kwargs)

    @property
    def file(self):
        return os.path.join(self.resource.dataset.mountpoint, self._file)
