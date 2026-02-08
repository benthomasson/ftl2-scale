#!/usr/bin/env python3
"""Provision N small Linodes for scale testing.

Usage:
    python provision.py 5           # spin up 5 nodes
    python provision.py 10          # spin up 10 nodes
    python provision.py --check 5   # dry run

Nodes are tracked in .ftl2-state.json. Re-running is safe — existing
nodes are reused. Use teardown.py to destroy them.

Environment variables:
    LINODE_TOKEN      - Linode API token (required)
    LINODE_ROOT_PASS  - Root password for servers
"""

import asyncio
import argparse
import os
from pathlib import Path
from ftl2 import automation


SERVER_TYPE = "g6-nanode-1"       # $5/mo, smallest
SERVER_IMAGE = "linode/fedora43"
SERVER_REGION = "us-east"
SERVER_PREFIX = "ftl2-scale"


async def main(count: int, check_mode: bool = False):
    print(f"Provisioning {count} nodes for scale testing")
    if check_mode:
        print("  Mode: CHECK (dry run)")
    print()

    ssh_pubkey = (Path.home() / ".ssh" / "id_rsa.pub").read_text().strip()

    async with automation(
        inventory="inventory.yml",
        secret_bindings={
            "community.general.linode_v4": {
                "access_token": "LINODE_TOKEN",
                "root_pass": "LINODE_ROOT_PASS",
            },
        },
        state_file=".ftl2-state.json",
        check_mode=check_mode,
        fail_fast=True,
        verbose=True,
        gate_modules="auto",
    ) as ftl:

        # Provision nodes
        created = 0
        for i in range(count):
            name = f"{SERVER_PREFIX}-{i}"

            if ftl.state.has(name):
                resource = ftl.state.get(name)
                print(f"  {name}: exists ({resource['ipv4'][0]})")
                continue

            print(f"  {name}: provisioning...")
            server = await ftl.local.community.general.linode_v4(
                label=name,
                type=SERVER_TYPE,
                region=SERVER_REGION,
                image=SERVER_IMAGE,
                authorized_keys=[ssh_pubkey],
                state="present",
            )

            if server.get("skipped"):
                print(f"  {name}: would be created (check mode)")
                continue

            ftl.state.add(name, {
                "provider": "linode",
                "id": server["instance"]["id"],
                "ipv4": server["instance"]["ipv4"],
                "label": name,
            })

            ftl.add_host(
                hostname=name,
                ansible_host=server["instance"]["ipv4"][0],
                ansible_user="root",
                groups=["scale"],
            )

            created += 1
            print(f"  {name}: created ({server['instance']['ipv4'][0]})")

        # Wait for SSH on new nodes
        if created > 0 and not check_mode:
            print(f"\nWaiting for SSH on {created} new node(s)...")
            await ftl.scale.wait_for_ssh(timeout=120)
            print("  All nodes reachable")

        # Summary
        total = sum(1 for _ in ftl.state.resources() if _.startswith(SERVER_PREFIX))
        print(f"\n{total} node(s) ready")

        # Write Ansible inventory for comparison tests
        _write_ansible_inventory(ftl)


def _write_ansible_inventory(ftl):
    """Write a static Ansible inventory from current state."""
    lines = ["[scale]"]
    for name in sorted(ftl.state.resources()):
        if name.startswith(SERVER_PREFIX):
            resource = ftl.state.get(name)
            ip = resource["ipv4"][0]
            lines.append(f"{name} ansible_host={ip} ansible_user=root")
    lines.append("")

    Path("ansible-inventory").write_text("\n".join(lines))
    print(f"Ansible inventory written to ansible-inventory ({len(lines) - 2} hosts)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision scale test nodes")
    parser.add_argument("count", type=int, help="Number of nodes to provision")
    parser.add_argument("--check", action="store_true", help="Dry run")
    args = parser.parse_args()
    asyncio.run(main(count=args.count, check_mode=args.check))
