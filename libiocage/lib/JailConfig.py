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
import re
import uuid

import libiocage.lib.JailConfigAddresses
import libiocage.lib.JailConfigDefaults
import libiocage.lib.JailConfigFstab
import libiocage.lib.JailConfigInterfaces
import libiocage.lib.JailConfigJSON
import libiocage.lib.JailConfigLegacy
import libiocage.lib.JailConfigResolver
import libiocage.lib.JailConfigZFS
import libiocage.lib.errors
import libiocage.lib.helpers


class JailConfig(dict, object):
    """
    Represents an iocage jail's configuration

    A jail configuration can be loaded from various formats that were used
    by different versions of iocage. Technically it is possible to store
    set properties in deprecated formats, but this might break when using
    newer features than the legacy version of iocage supports. It is
    recommended to use the reading capabilities to migrate to the JSON
    config format.

    Supported Configuration Formats:

        JSON: (current)
            Since the Python 3 implementation iocage stored jail configs in
            a file called `config.json` within the jail's root dataset

        ZFS:
            iocage-legacy written in Bash used to save jail configurations
            as ZFS properties on the jail's root dataset. Due to poor
            performance and easier readability this format later was replaced
            with a file based config storage. Even though it is a deprecated
            format, libiocage is compatible to read a jail config from ZFS.

        UCL:
            Yet another deprecated configuration format, that libiocage also
            supports reading from. A legacy version of iocage used this format.

    Special Properties:

        Special properties are

    """

    def __init__(self,
                 data={},
                 jail=None,
                 logger=None,
                 new=False,
                 defaults_file=None):

        dict.__init__(self)

        libiocage.lib.helpers.init_logger(self, logger)

        self.data = {}
        self.special_properties = {}
        self["legacy"] = False

        # jail is required for various operations (write, fstab, etc)
        if jail:
            self.jail = jail
            fstab = libiocage.lib.JailConfigFstab.JailConfigFstab(
                jail=jail,
                logger=self.logger
            )
            self.fstab = fstab
        else:
            self.jail = None
            self.fstab = None

        # the name is used in many other variables and needs to be set first
        self["id"] = None
        for key in ["id", "name", "uuid"]:
            if key in data.keys():
                self["name"] = data[key]
                break

        # be aware of iocage-legacy jails for migration
        try:
            self["legacy"] = data["legacy"] is True
        except:
            self["legacy"] = False

        self.defaults_file = defaults_file
        self._defaults = None

        self.clone(data)

    @property
    def defaults(self):
        if self._defaults is None:
            self._load_defaults()
        return self._defaults

    def _load_defaults(self, defaults_file=None):

        if defaults_file is not None:
            self.defaults_file = defaults_file

        if defaults_file is None and self.jail is not None:
            root_mountpoint = self.jail.host.datasets.root.mountpoint
            defaults_file = f"{root_mountpoint}/defaults.json"

        self._defaults = libiocage.lib.JailConfigDefaults.JailConfigDefaults(
            file=defaults_file,
            logger=self.logger
        )

    def clone(self, data, skip_on_error=False):
        """
        Apply data from a data dictionary to the JailConfig

        Existing jail configuration is not emptied using.

        Args:

            data (dict):
                Dictionary containing the configuration to apply

            skip_on_error (bool):
                Passed to __setitem__

        """
        current_id = self["id"]
        for key, value in data.items():

            if (key in ["id", "name", "uuid"]) and (current_id is not None):
                value = current_id

            self.__setitem__(key, value, skip_on_error=skip_on_error)

    def read(self):

        if libiocage.lib.JailConfigJSON.JailConfigJSON.exists(self):

            libiocage.lib.JailConfigJSON.JailConfigJSON.read(self)
            self["legacy"] = False
            self.logger.log("Configuration loaded from JSON", level="verbose")
            return "json"

        elif libiocage.lib.JailConfigLegacy.JailConfigLegacy.exists(self):

            libiocage.lib.JailConfigLegacy.JailConfigLegacy.read(self)
            self["legacy"] = True
            self.logger.verbose(
                "Configuration loaded from UCL config file (iocage-legacy)")
            return "ucl"

        elif libiocage.lib.JailConfigZFS.JailConfigZFS.exists(self):

            libiocage.lib.JailConfigZFS.JailConfigZFS.read(self)
            self["legacy"] = True
            self.logger.verbose(
                "Configuration loaded from ZFS properties (iocage-legacy)")
            return "zfs"

        else:

            self.logger.debug("No configuration was found")
            return None

    def update_special_property(self, name):

        try:
            self.data[name] = str(self.special_properties[name])
        except KeyError:
            # pass when there is no handler for the notifying propery
            pass

    def attach_special_property(self, name, special_property):
        self.special_properties[name] = special_property

    def save(self):
        if not self["legacy"]:
            self.save_json()
        else:
            libiocage.lib.JailConfigLegacy.JailConfigLegacy.save(self)

        self.jail.rc_conf.save()

    def save_json(self):
        libiocage.lib.JailConfigJSON.JailConfigJSON.save(self)

    def _set_name(self, name, **kwargs):

        try:
            # We do not want to set the same name twice.
            # This can occur when the Jail is initialized
            # with it's name and the same name is read from
            # the configuration
            if self.id == name:
                return
        except:
            pass

        allowed_characters_pattern = "([^A-z0-9\\._\\-]|\\^)"
        invalid_characters = re.findall(allowed_characters_pattern, name)
        if len(invalid_characters) > 0:
            msg = (
                f"Invalid character in name: "
                " ".join(invalid_characters)
            )
            self.logger.error(msg)

        is_valid_name = libiocage.lib.helpers.validate_name(name)
        if is_valid_name is True:
            self["id"] = name
        else:
            try:
                self["id"] = str(uuid.UUID(name))  # legacy support
            except:
                raise libiocage.lib.errors.InvalidJailName(logger=self.logger)

        self.logger.spam(
            f"Set jail name to {name}",
            jail=self.jail
        )

    def _get_type(self):

        if self["basejail"]:
            return "basejail"
        elif self["clonejail"]:
            return "clonejail"
        else:
            return "jail"

    def _set_type(self, value, **kwargs):

        if value == "basejail":
            self["basejail"] = True
            self["clonejail"] = False
            self.data["type"] = "jail"

        elif value == "clonejail":
            self["basejail"] = False
            self["clonejail"] = True
            self.data["type"] = "jail"

        else:
            self.data["type"] = value

    def _get_basejail(self):
        return libiocage.lib.helpers.parse_user_input(self.data["basejail"])

    def _default_basejail(self):
        return False

    def _set_basejail(self, value, **kwargs):
        if self["legacy"]:
            self.data["basejail"] = libiocage.lib.helpers.to_string(
                value, true="on", false="off")
        else:
            self.data["basejail"] = libiocage.lib.helpers.to_string(
                value, true="yes", false="no")

    def _get_clonejail(self):
        return libiocage.lib.helpers.parse_user_input(self.data["clonejail"])

    def _default_clonejail(self):
        return True

    def _set_clonejail(self, value, **kwargs):
        self.data["clonejail"] = libiocage.lib.helpers.to_string(
            value, true="on", false="off")

    def _get_ip4_addr(self):
        try:
            return self.special_properties["ip4_addr"]
        except:
            return None

    def _set_ip4_addr(self, value, **kwargs):
        ip4_addr = libiocage.lib.JailConfigAddresses.JailConfigAddresses(
            value,
            jail_config=self,
            property_name="ip4_addr",
            logger=self.logger
        )
        self.special_properties["ip4_addr"] = ip4_addr
        self.update_special_property("ip4_addr")

    def _get_ip6_addr(self):
        try:
            return self.special_properties["ip6_addr"]
        except:
            return None

    def _set_ip6_addr(self, value, **kwargs):
        ip6_addr = libiocage.lib.JailConfigAddresses.JailConfigAddresses(
            value,
            jail_config=self,
            property_name="ip6_addr",
            logger=self.logger,
            skip_on_error=self._skip_on_error(**kwargs)
        )
        self.special_properties["ip6_addr"] = ip6_addr
        self.update_special_property("ip6_addr")

        rc_conf = self.jail.rc_conf
        rc_conf["rtsold_enable"] = "accept_rtadv" in str(value)

    def _get_interfaces(self):
        return self.special_properties["interfaces"]

    def _set_interfaces(self, value, **kwargs):
        interfaces = libiocage.lib.JailConfigInterfaces.JailConfigInterfaces(
            value,
            jail_config=self
        )
        self.special_properties["interfaces"] = interfaces
        self.update_special_property("interfaces")

    def _get_defaultrouter(self):
        value = self.data['defaultrouter']
        return value if (value != "none" and value is not None) else None

    def _set_defaultrouter(self, value, **kwargs):
        if value is None:
            value = 'none'
        self.data['defaultrouter'] = value

    def _get_defaultrouter6(self):
        value = self.data['defaultrouter6']
        return value if (value != "none" and value is not None) else None

    def _set_defaultrouter6(self, value, **kwargs):
        if value is None:
            value = 'none'
        self.data['defaultrouter6'] = value

    def _get_vnet(self):
        return libiocage.lib.helpers.parse_user_input(self.data["vnet"])

    def _set_vnet(self, value, **kwargs):
        self.data["vnet"] = libiocage.lib.helpers.to_string(
            value, true="on", false="off")

    def _get_jail_zfs_dataset(self):
        try:
            return self.data["jail_zfs_dataset"].split()
        except KeyError:
            return []

    def _set_jail_zfs_dataset(self, value, **kwargs):
        value = [value] if isinstance(value, str) else value
        self.data["jail_zfs_dataset"] = " ".join(value)

    def _get_jail_zfs(self):
        try:
            enabled = libiocage.lib.helpers.parse_user_input(
                self.data["jail_zfs"]
            )
        except:
            enabled = self._default_jail_zfs()

        if not enabled:
            if len(self["jail_zfs_dataset"]) > 0:
                raise libiocage.lib.errors.JailConigZFSIsNotAllowed(
                    logger=self.logger
                )
        return enabled

    def _set_jail_zfs(self, value, **kwargs):
        if (value is None) or (value == ""):
            del self.data["jail_zfs"]
            return
        self.data["jail_zfs"] = libiocage.lib.helpers.to_string(
            value,
            true="on",
            false="off"
        )

    def _default_jail_zfs(self):
        # if self.data["jail_zfs"] does not explicitly exist,
        # _get_jail_zfs would raise
        try:
            return len(self["jail_zfs_dataset"]) > 0
        except:
            return False

    def _get_resolver(self):
        return self.__get_or_create_special_property_resolver()

    def _set_resolver(self, value, **kwargs):

        if isinstance(value, str):
            self.data["resolver"] = value
            resolver = self["resolver"]
        else:
            resolver = libiocage.lib.JailConfigResolver.JailConfigResolver(
                jail_config=self,
                logger=self.logger
            )
        resolver.update(value, notify=True)

    def _get_cloned_release(self):
        try:
            return self.data["cloned_release"]
        except:
            return self["release"]

    def _get_basejail_type(self):

        # first see if basejail_type was explicitly set
        try:
            return self.data["basejail_type"]
        except:
            pass

        # if it was not, the default for is 'nullfs' if the jail is a basejail
        try:
            if self["basejail"]:
                return "nullfs"
        except:
            pass

        # otherwise the jail does not have a basejail_type
        return None

    def _get_login_flags(self):
        try:
            return JailConfigList(self.data["login_flags"].split())
        except KeyError:
            return JailConfigList(["-f", "root"])

    def _set_login_flags(self, value, **kwargs):
        if value is None:
            try:
                del self.data["login_flags"]
            except:
                pass
        else:
            if isinstance(value, list):
                self.data["login_flags"] = " ".join(value)
            elif isinstance(value, str):
                self.data["login_flags"] = value
            else:
                raise libiocage.lib.errors.InvalidJailConfigValue(
                    property_name="login_flags",
                    logger=self.logger
                )

    def _set_tags(self, value, **kwargs):
        if isinstance(value, str):
            self.tags = value.split(",")
        elif isinstance(value, list):
            self.tags = set(value)
        elif isinstance(value, set):
            self.tags = value
        else:
            raise libiocage.lib.errors.InvalidJailConfigValue(
                property_name="tags",
                logger=self.logger
            )

    def _get_host_hostname(self):
        try:
            return self.data["host_hostname"]
        except KeyError:
            return self.jail.humanreadable_name

    def _get_host_hostuuid(self):
        try:
            return self.data["host_hostuuid"]
        except KeyError:
            return self["id"]

    def __get_or_create_special_property_resolver(self):

        try:
            return self.special_properties["resolver"]
        except:
            pass

        resolver = libiocage.lib.JailConfigResolver.JailConfigResolver(
            jail_config=self,
            logger=self.logger
        )
        resolver.update(notify=False)
        self.special_properties["resolver"] = resolver

        return self.special_properties["resolver"]

    def get_string(self, key):
        return self.__getitem__(key, string=True)

    def _skip_on_error(self, **kwargs):
        """
        A helper to resolve skip_on_error attribute
        """
        try:
            return kwargs["skip_on_error"] is True
        except AttributeError:
            return False

    def __getitem_user(self, key, string=False):

        # passthrough existing properties
        try:
            return self.stringify(self.__getattribute__(key), string)
        except:
            pass

        # data with mappings
        try:
            get_method = self.__getattribute__(f"_get_{key}")
            return self.stringify(get_method(), string)
        except:
            pass

        # plain data attribute
        try:
            return self.stringify(self.data[key], string)
        except:
            pass

        raise KeyError(f"User defined property not found: {key}")

    def __getitem__(self, key, string=False):

        try:
            return self.__getitem_user(key, string)
        except:
            pass

        # fall back to default
        return self.defaults[key]

    def __delitem__(self, key):
        del self.data[key]

    def __setitem__(self, key, value, **kwargs):

        # passthrough existing properties
        # try:
        #     self.__getitem__(key)
        #     object.__setitem__(self, key, value)
        #     return
        # except:
        #     pass

        parsed_value = libiocage.lib.helpers.parse_user_input(value)

        setter_method = None
        try:
            setter_method = self.__getattribute__(f"_set_{key}")
        except:
            self.data[key] = parsed_value
            pass

        if setter_method is not None:
            return setter_method(parsed_value, **kwargs)

    def set(self, key: str, value, **kwargs) -> bool:
        """
        Set a JailConfig property

        Args:

            key:
                The jail config property name

            value:
                Value to set the property to

            **kwargs:
                Arguments from **kwargs are passed to setter functions

        Returns:

            bool: True if the JailConfig was changed
        """

        try:
            hash_before = str(self.__getitem_user(key)).__hash__()
        except Exception:
            hash_before = None
            pass

        self.__setitem__(key, value, **kwargs)

        try:
            hash_after = str(self.__getitem_user(key)).__hash__()
        except Exception:
            hash_after = None
            pass

        return (hash_before != hash_after)

    def __str__(self):
        return libiocage.lib.JailConfigJSON.JailConfigJSON.toJSON(self)

    def __dir__(self):

        properties = set()

        for prop in dict.__dir__(self):
            if prop.startswith("_default_"):
                properties.add(prop[9:])
            elif not prop.startswith("_"):
                properties.add(prop)

        for key in self.data.keys():
            properties.add(key)

        return list(properties)

    @property
    def all_properties(self):

        properties = set()

        for prop in dict.__dir__(self):
            if prop.startswith("_default_"):
                properties.add(prop[9:])

        for key in self.data.keys():
            properties.add(key)

        return list(properties)

    def stringify(self, value, enabled=True):
        return libiocage.helpers.to_string if (enabled is True) else value


class JailConfigList(list):

    def __str__(self):
        return " ".join(self)
