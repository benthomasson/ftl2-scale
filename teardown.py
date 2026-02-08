#!/usr/bin/env python3
"""Destroy all scale test nodes.

Usage:
    python teardown.py          # destroy all nodes
    python teardown.py --check  # dry run

Reads .ftl2-state.json and destroys all ftl2-scale-* resources.

Environment variables:
    LINODE_TOKEN - Linode API token (required)
"""

import asyncio
import argparse
from pathlib import Path
from ftl2 import automation


SERVER_PREFIX = "ftl2-scale"


async def main(check_mode: bool = False):
    print("Tearing down scale test nodes")
    if check_mode:
        print("  Mode: CHECK (dry run)")
    print()

    async with automation(
        inventory="inventory.yml",
        secret_bindings={
            "community.general.linode_v4": {
                "access_token": "LINODE_TOKEN",
            },
        },
        state_file=".ftl2-state.json",
        check_mode=check_mode,
        fail_fast=True,
        verbose=True,
    ) as ftl:

        names = [n for n in ftl.state.resources() if n.startswith(SERVER_PREFIX)]

        if not names:
            print("  No scale test nodes found in state")
            return

        print(f"  Destroying {len(names)} node(s)...")
        for name in sorted(names):
            resource = ftl.state.get(name)
            print(f"  {name} ({resource['ipv4'][0]}): destroying...")

            await ftl.local.community.general.linode_v4(
                label=name,
                state="absent",
            )

            ftl.state.remove(name)
            print(f"  {name}: destroyed")

        print(f"\n{len(names)} node(s) destroyed")

    # Clean up ansible inventory
    inv = Path("ansible-inventory")
    if inv.exists():
        inv.unlink()
        print("Ansible inventory removed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Destroy scale test nodes")
    parser.add_argument("--check", action="store_true", help="Dry run")
    args = parser.parse_args()
    asyncio.run(main(check_mode=args.check))
