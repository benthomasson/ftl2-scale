#!/usr/bin/env python3
# /// script
# dependencies = ["ftl2 @ git+https://github.com/benthomasson/ftl2"]
# requires-python = ">=3.13"
# ///
"""Run scale tests against provisioned nodes.

Usage:
    uv run scale_test.py --setup              # create Ansible venv
    uv run scale_test.py                      # run all tests
    uv run scale_test.py --test gather_facts  # run one test
    uv run scale_test.py --json results.json

Expects nodes to be provisioned via provision.py first.
Runs each test with both Ansible (via ansible-playbook in .venv-ansible/)
and FTL2, measuring wall-clock time.

FTL2 modifies the ansible package at import time, so Ansible must run
in a separate virtual environment.

Environment variables:
    LINODE_TOKEN      - Linode API token (for API tests)
    LINODE_ROOT_PASS  - Root password
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from ftl2 import automation


SERVER_PREFIX = "ftl2-scale"
ANSIBLE_VENV = Path(".venv-ansible")


def get_ansible_playbook() -> str:
    """Return path to ansible-playbook in the Ansible venv."""
    path = ANSIBLE_VENV / "bin" / "ansible-playbook"
    if not path.exists():
        print(f"Ansible venv not found at {ANSIBLE_VENV}")
        print("Run: uv run scale_test.py --setup")
        sys.exit(1)
    return str(path)


def setup_ansible_venv():
    """Create a separate venv with Ansible installed."""
    if not ANSIBLE_VENV.exists():
        print(f"Creating Ansible venv at {ANSIBLE_VENV}...")
        subprocess.run(["uv", "venv", str(ANSIBLE_VENV)], check=True)
    else:
        print(f"Ansible venv exists at {ANSIBLE_VENV}")

    print("Installing Ansible...")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(ANSIBLE_VENV / "bin" / "python"), "ansible"],
        check=True,
    )
    print("Ansible venv ready")


async def count_hosts() -> int:
    """Count provisioned hosts from state."""
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
    ) as ftl:
        return sum(1 for n in ftl.state.resources() if n.startswith(SERVER_PREFIX))


# --- FTL2 tests ---

async def ftl2_gather_facts():
    """Gather facts from all hosts."""
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
        gate_modules="auto",
        fail_fast=True,
    ) as ftl:
        await ftl.scale.setup()


async def ftl2_file_operations():
    """Create, stat, and remove files on all hosts."""
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
        gate_modules="auto",
        fail_fast=True,
    ) as ftl:
        for i in range(5):
            await ftl.scale.file(path=f"/tmp/ftl2_scale_{i}", state="touch")
        for i in range(5):
            await ftl.scale.stat(path=f"/tmp/ftl2_scale_{i}")
        for i in range(5):
            await ftl.scale.file(path=f"/tmp/ftl2_scale_{i}", state="absent")


async def ftl2_install_package():
    """Install and remove a small package on all hosts."""
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
        gate_modules="auto",
        fail_fast=True,
    ) as ftl:
        await ftl.scale.command(cmd="dnf install -y python3-dnf")
        await ftl.scale.dnf(name="tree", state="present")
        await ftl.scale.dnf(name="tree", state="absent")


async def ftl2_copy_and_template():
    """Copy config files to all hosts."""
    async with automation(
        inventory="inventory.yml",
        state_file=".ftl2-state.json",
        gate_modules="auto",
        fail_fast=True,
    ) as ftl:
        for i in range(3):
            await ftl.scale.copy(
                dest=f"/tmp/ftl2_scale_config_{i}.conf",
                content=f"# Config {i}\nworkers = {i * 2}\nport = {8080 + i}\n",
                mode="0644",
            )
        for i in range(3):
            await ftl.scale.file(path=f"/tmp/ftl2_scale_config_{i}.conf", state="absent")


# --- Test registry ---

TESTS = {
    "gather_facts": {
        "description": "Gather facts from all hosts",
        "ftl2": ftl2_gather_facts,
        "playbook": "playbooks/gather_facts.yml",
    },
    "file_operations": {
        "description": "5x file create/stat/remove on all hosts (15 tasks)",
        "ftl2": ftl2_file_operations,
        "playbook": "playbooks/file_operations.yml",
    },
    "install_package": {
        "description": "Install and remove a package on all hosts",
        "ftl2": ftl2_install_package,
        "playbook": "playbooks/install_package.yml",
    },
    "copy_and_template": {
        "description": "Copy 3 config files to all hosts, then clean up",
        "ftl2": ftl2_copy_and_template,
        "playbook": "playbooks/copy_and_template.yml",
    },
}


# --- Runner ---

def run_ansible(playbook: str, inventory: str = "ansible-inventory") -> tuple[bool, float]:
    """Run an Ansible playbook using the separate Ansible venv."""
    if not Path(playbook).exists():
        return False, 0.0
    ansible_playbook = get_ansible_playbook()
    start = time.perf_counter()
    result = subprocess.run(
        [ansible_playbook, playbook, "-i", inventory],
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        print(f"    STDERR: {result.stderr[-200:]}" if result.stderr else "")
    return result.returncode == 0, elapsed


async def run_ftl2(func) -> tuple[bool, float]:
    """Run an FTL2 test function, return (success, seconds)."""
    start = time.perf_counter()
    try:
        await func()
        elapsed = time.perf_counter() - start
        return True, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"    ERROR: {e}")
        return False, elapsed


async def main():
    parser = argparse.ArgumentParser(description="FTL2 scale tests")
    parser.add_argument("--setup", action="store_true", help="Create Ansible venv")
    parser.add_argument("--test", type=str, help="Run a specific test")
    parser.add_argument("--json", type=str, metavar="FILE", help="Write results to JSON")
    parser.add_argument("--ftl2-only", action="store_true", help="Skip Ansible tests")
    parser.add_argument("--ansible-only", action="store_true", help="Skip FTL2 tests")
    args = parser.parse_args()

    if args.setup:
        setup_ansible_venv()
        return

    # Check we have hosts
    host_count = await count_hosts()
    if host_count == 0:
        print("No hosts provisioned. Run: uv run provision.py <count>")
        sys.exit(1)

    tests_to_run = {args.test: TESTS[args.test]} if args.test else TESTS

    print(f"Scale test: {host_count} hosts, {len(tests_to_run)} test(s)")
    print(f"{'=' * 60}")

    all_results = []

    for name, test in tests_to_run.items():
        print(f"\n  {name}: {test['description']}")
        result = {"name": name, "description": test["description"], "hosts": host_count}

        # Ansible
        if not args.ftl2_only:
            success, elapsed = run_ansible(test["playbook"])
            status = "ok" if success else "FAIL"
            print(f"    Ansible: {elapsed:.3f}s [{status}]")
            result["ansible"] = {"time": round(elapsed, 3), "success": success}

        # FTL2
        if not args.ansible_only:
            success, elapsed = await run_ftl2(test["ftl2"])
            status = "ok" if success else "FAIL"
            print(f"    FTL2:    {elapsed:.3f}s [{status}]")
            result["ftl2"] = {"time": round(elapsed, 3), "success": success}

        # Speedup
        if "ansible" in result and "ftl2" in result:
            if result["ansible"]["success"] and result["ftl2"]["success"]:
                speedup = result["ansible"]["time"] / result["ftl2"]["time"]
                print(f"    Speedup: {speedup:.1f}x")
                result["speedup"] = round(speedup, 2)

        all_results.append(result)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY ({host_count} hosts)")
    print(f"{'=' * 60}")
    print(f"  {'Test':<25s} {'Ansible':>10s} {'FTL2':>10s} {'Speedup':>10s}")
    print(f"  {'-'*25:<25s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s}")
    for r in all_results:
        a_t = f"{r['ansible']['time']:.3f}s" if r.get("ansible", {}).get("success") else "n/a"
        f_t = f"{r['ftl2']['time']:.3f}s" if r.get("ftl2", {}).get("success") else "n/a"
        sp = f"{r['speedup']:.1f}x" if "speedup" in r else "n/a"
        print(f"  {r['name']:<25s} {a_t:>10s} {f_t:>10s} {sp:>10s}")

    if args.json:
        Path(args.json).write_text(json.dumps(all_results, indent=2) + "\n")
        print(f"\nResults written to {args.json}")


if __name__ == "__main__":
    asyncio.run(main())
