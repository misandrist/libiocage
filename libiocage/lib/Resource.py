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

    ZFS_PROPERTY_PREFIX = "org.freebsd.iocage:"

    CONFIG_TYPES = (
        "json",
        "legacy",
        "zfs"
    )

    DEFAULT_JSON_FILE = "config.json"
    DEFAULT_LEGACY_FILE = "config"

    def __init__(
        self,
        config_type: str="auto",
        config_file: str=None,  # 'config.json', 'config', etc
        logger: libzfs.lib.Logger.Logger=None,
        zfs: libzfs.ZFS=None
    ):

        libiocage.lib.helpers.init_zfs(self, zfs)
        libiocage.lib.helpers.init_logger(self, logger)

        self._config_file = config_file
        self._config_type = None
        self.config_type = self.CONFIG_TYPES.index(config_type)

    @property
    def dataset(self):
        return None

    @property
    def path(self):
        """
        Mountpoint of the jail's base ZFS dataset
        """
        return self.dataset.mountpoint

    @property
    def legacy_config_path(self):
        return os.path.join(self.dataset.mountpoint, "config")

    @property
    def config_type(self):
        if self._config_type == self.CONFIG_TYPES.index("auto"):
            self._config_type = self._find_config_type()
        return self._config_type

    @config_type.setter
    def config_type(self, value):
        self._config_type = self.CONFIG_TYPES.index(value)

    def _find_config_type(self):

        if os.path.isfile(self.abspath(self.DEFAULT_JSON_FILE)):
            return self.CONFIG_TYPES.index("json")

        if os.path.isfile(self.abspath(self.DEFAULT_LEGACY_FILE)):
            return self.CONFIG_TYPES.index("legacy")

        for prop_name in self.dataset.properties.keys():
            if prop_name.startswith(self.ZFS_PROPERTY_PREFIX):
                return self.CONFIG_TYPES.index("zfs")

        return self.CONFIG_TYPES[0]

    @property
    def config_file(self):
        """
        Relative path of the resource config file
        """
        if self._config_file is not None:
            return self._config_file

        if self.config_type == "json":
            return self.DEFAULT_JSON_FILE

        if self.config_type == "legacy":
            return self.DEFAULT_LEGACY_FILE

        return None

    def abspath(self, relative_path: str) -> str:
        return os.path.join(self.dataset.mountpoint, relative_path)

    def write_config(self, data: dict):
        return self.config_handler.write(data)

    def read_config(self):
        return self.config_handler.read()

    @property
    def config_handler(self):

        if self.config_type == "json":
            handler = libiocage.lib.ConfigJSON.ResourceConfigJSON
        elif self.config_type == "zfs":
            handler = libiocage.lib.ConfigJSON.ResourceConfigZFS
        elif self.config_type == "json":
            handler = libiocage.lib.ConfigJSON.ConfigJSON

        return handler(
            resource=self,
            logger=self.logger
        )


class DefaultResource(Resource):

    DEFAULT_JSON_FILE = "defaults.json"
    DEFAULT_LEGACY_FILE = "defaults"


class DatasetResource(Resource):

    self.dataset = dataset

    def __init__(
        self,
        dataset: libzfs.ZFSDataset,
        **kwargs
    ):

        Resource.__init__(self)
        self._dataset = dataset

class JailResource(Resource):

    def __init__(
        self,
        jail: libiocage.lib.Jail.Jail,
        dataset_name: str=None,
        **kwargs
    ):

        self.jail = jail
        self._fstab = None
        self._dataset_name = dataset_name
        Resource.__init__(self, **kwargs)

    @property
    def fstab(self):
        if self._fstab is None:
            self.fstab = libiocage.lib.JailConfigFstab.JailConfigFstab(
                jail=self.jail,
                logger=self.logger
            )

    @property
    def dataset_name(self):
        """
        Name of the jail's base ZFS dataset
        """
        if self._dataset_name is not None:
            return self._dataset_name
        else:
            root_dataset_name = self.jail.host.datasets.root.name
            jail_id = self.config["id"]
            return f"{root_dataset_name}/jails/{jail_id}"

    @dataset_name.setter
    def dataset_name(self, value=None):
        self._dataset_name = value

    @property
    def dataset(self):
        """
        The jail's base ZFS dataset
        """
        return self.zfs.get_dataset(self.dataset_name)


def createNewResource(
    dataset_name: str,
    zfs: libzfs.ZFS=None,
    **kwargs
):

    libiocage.lib.helpers.init_zfs(self, zfs)
    libiocage.lib.helpers.init_logger(self, logger)
    
    try:
        dataset = zfs.get_dataset(dataset_name)
    except:
        pool_name = dataset_name[0:dataset_name.index("/")]
        pool = _find_pool(pool_name, zfs)
        pool.create(dataset_name, {}, create_ancestors=True)
        dataset = zfs.get_dataset(dataset_name)
        dataset.mount()

    Resource.__init__(self, dataset, zfs=zfs, **kwargs)


def getExistingOrNewResource(
    dataset_name: str,
    zfs: libzfs.ZFS=None,
    **kwargs
):

    try:
        dataset = zfs.get_dataset(dataset_name)
    except:
        return createNewResource(
            self,
            dataset_name=dataset_name,
            zfs=zfs,
            **kwargs
        )

    return Resource.__init__(
        self,
        dataset=dataset,
        zfs=zfs,
        **kwargs
    )


def _find_pool(
    self,
    pool_name,
    zfs
) -> libzfs.ZFSPool:

    for pool in zfs.pools:
        if pool.name == pool_name:
            return pool
    return None
