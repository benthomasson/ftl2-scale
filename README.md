# ftl2-scale

Scale testing FTL2 vs Ansible across many remote hosts.

Provisions N small Linodes (Nanodes, $5/mo each), runs identical workloads through both FTL2 and `ansible-playbook`, and compares wall-clock times.

## Setup

```bash
# Set credentials
export LINODE_TOKEN="your-token"
export LINODE_ROOT_PASS="your-password"
```

No manual install needed. Scripts use [PEP 723 inline metadata](https://peps.python.org/pep-0723/) so `uv run` installs ftl2 automatically.

## Usage

```bash
# Provision 5 nodes
uv run provision.py 5

# Run scale tests
uv run scale_test.py

# Run a specific test
uv run scale_test.py --test file_operations

# Save results
uv run scale_test.py --json results.json

# Tear down all nodes when done
uv run teardown.py
```

## Tests

| Test | Description |
|------|-------------|
| gather_facts | Gather system facts from all hosts |
| file_operations | 5x create/stat/remove on all hosts (15 tasks) |
| install_package | dnf install + remove on all hosts |
| copy_and_template | Copy 3 config files to all hosts, then clean up |

## Cost

Nanodes are $0.0075/hr each. A 10-node test running for 1 hour costs $0.075. Always run `uv run teardown.py` when done.
