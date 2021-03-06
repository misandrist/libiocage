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
"""get module for the cli."""
import click

import libiocage.lib.Host
import libiocage.lib.Jail
import libiocage.lib.Logger


@click.command(context_settings=dict(
    max_content_width=400, ), name="get", help="Gets the specified property.")
@click.pass_context
@click.argument("prop", required=True, default="")
@click.argument("jail", required=True, default="")
@click.option("--all", "-a", "_all", help="Get all properties for the "
                                          "specified jail.", is_flag=True)
@click.option("--pool", "-p", "_pool", help="Get the currently activated "
                                            "zpool.", is_flag=True)
@click.option("--log-level", "-d", default="info")
def cli(ctx, prop, _all, _pool, jail, log_level):
    """Get a list of jails and print the property."""

    logger = ctx.parent.logger
    logger.print_level = log_level
    host = libiocage.lib.Host.Host(logger=logger)

    if _pool is True:
        try:
            print(host.datasets.active_pool.name)
        except Exception:
            print("No active pool found")
        exit(1)

    if jail == "":
        prop = ""

    jail_identifier = jail
    jail = libiocage.lib.Jail.Jail(
        jail_identifier,
        host=host,
        logger=logger
    )

    if not jail.exists:
        logger.error(f"Jail '{jail.name}' does not exist")
        exit(1)

    if _all is True:
        prop = None

    if prop == "all":
        prop = None

    if (prop is None) and (jail_identifier == "") and not _all:
        logger.error("Missing arguments property and jail")
        exit(1)
    elif (prop is not None) and (jail_identifier == ""):
        logger.error("Missing argument property name or -a/--all argument")
        exit(1)

    if prop:
        value = _lookup_jail_value(jail, prop)

        if value:
            print(value)
            return
        else:
            logger.error(f"Unknown property '{prop}'")
            exit(1)

    for key in jail.config["all_properties"]:
        if (prop is None) or (key == prop):
            value = jail.config["get_string"](key)
            print_property(key, value)


def print_property(key, value):
    print(f"{key}:{value}")


def _lookup_jail_value(jail, key):
    if key in libiocage.lib.Jails.Jails.JAIL_KEYS:
        return jail.getstring(key)
    else:
        if key == "running":
            return jail.running

        val = str(jail.config.__getitem__(key))

        return val if val is not None else False
