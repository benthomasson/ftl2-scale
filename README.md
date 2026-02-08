# ftl2-scale

Scale testing FTL2 vs Ansible across many remote hosts.

Provisions N small Linodes (Nanodes, $5/mo each), runs identical workloads through both FTL2 and `ansible-playbook`, and compares wall-clock times.

## Setup

```bash
# Install ftl2
uvx --from "git+https://github.com/benthomasson/ftl2" ftl2

# Set credentials
export LINODE_TOKEN="your-token"
export LINODE_ROOT_PASS="your-password"
```

## Usage

```bash
# Provision 5 nodes
python provision.py 5

# Run scale tests
python scale_test.py

# Run a specific test
python scale_test.py --test file_operations

# Save results
python scale_test.py --json results.json

# Tear down all nodes when done
python teardown.py
```

## Tests

| Test | Description |
|------|-------------|
| gather_facts | Gather system facts from all hosts |
| file_operations | 5x create/stat/remove on all hosts (15 tasks) |
| install_package | dnf install + remove on all hosts |
| copy_and_template | Copy 3 config files to all hosts, then clean up |

## Cost

Nanodes are $0.0075/hr each. A 10-node test running for 1 hour costs $0.075. Always run `python teardown.py` when done.
