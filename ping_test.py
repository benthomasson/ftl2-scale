#!/usr/bin/env python3
# /// script
# dependencies = ["ftl2 @ git+https://github.com/benthomasson/ftl2"]
# requires-python = ">=3.13"
# ///
"""Ping all provisioned nodes to check connectivity.

Usage:
    uv run ping_test.py
"""

import asyncio
from ftl2 import automation


SERVER_PREFIX = "ftl2-scale"


async def main():
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
        gate_modules="auto",
    ) as ftl:
        names = [n for n in ftl.state.resources() if n.startswith(SERVER_PREFIX)]
        if not names:
            print("No nodes in state")
            return

        print(f"Pinging {len(names)} node(s)...")
        await ftl.scale.ping()


if __name__ == "__main__":
    asyncio.run(main())
