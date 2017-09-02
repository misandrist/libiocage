import os.path

import libzfs

import libiocage.lib.helpers


class Resource:
    """
    iocage resource

    An iocage resource is the representation of a jail, release or base release.

    File Structure:

        <ZFSDataset>/root:
            
            This dataset contains the root filesystem of a jail or release.

            In case of a ZFS basejail resource it hosts a tree of child
            datasets that may be cloned into an existing target dataset.

        <ZFSDataset>/config.json:

            The resource configuration in JSON format

        <ZFSDataset>/config:
    
            The resource configuration in legacy format

        <ZFSDataset>.properties: 

            iocage legacy used to store resource configuration in ZFS
            properties on the resource dataset

    """

    CONFIG_TYPES: (
        "json",
        "legacy",
        "zfs"
    )

    def __init__(
        self,
        dataset: libzfs.ZFSDataset,
        config_type: str="auto"
    ):

        self.dataset = dataset
        self.config_type = self.CONFIG_TYPES.index(config_type)

    @property
    def json_config_path(self):
        return os.path.join(self.dataset.mountpoint, "config.json")

    @property
    def legacy_config_path(self):
        return os.path.join(self.dataset.mountpoint, "config")

    @property
    def config_type(self):
        if self._config_type == self.CONFIG_TYPES.index("auto"):
            self._config_type = self._find_config_type()
        return self._config_type

    def _find_config_type(self):

        basedir = self.dataset.mountpoint

        if os.path.isfile(self.json_config_path):
            return self.CONFIG_TYPES.index("json")



class NewResource(Resource):

    def __init__(self, dataset_name, *args, logger=None, **kwargs):

        libiocage.lib.helpers.init_logger(self, logger)
