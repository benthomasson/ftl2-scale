# CLAUDE.md

## What This Is

Scale testing repo for FTL2 vs Ansible. Provisions many small Linodes and runs identical workloads through both frameworks to compare remote execution performance at scale.

## Key Files

```
provision.py          # Spin up N Nanodes, tracked in .ftl2-state.json
teardown.py           # Destroy all scale test nodes
scale_test.py         # Run tests with both FTL2 and Ansible, compare times
inventory.yml         # Empty group, populated at runtime via state file
ansible-inventory     # Generated static inventory for ansible-playbook
playbooks/            # Ansible playbooks (one per test)
```

## Workflow

```bash
export LINODE_TOKEN="..." LINODE_ROOT_PASS="..."

python provision.py 5         # create 5 nodes
python scale_test.py          # run all tests
python scale_test.py --json results.json
python teardown.py            # destroy all nodes
```

## Important

- **Always tear down** — `python teardown.py` destroys all nodes. Nanodes cost $0.0075/hr each.
- **State file is ground truth** — `.ftl2-state.json` tracks what exists. Re-running provision.py is safe.
- **Ansible needs its own inventory** — `provision.py` writes `ansible-inventory` for `ansible-playbook` to use.
- **FTL2 uses state file** — reads `.ftl2-state.json` + `inventory.yml` to find hosts dynamically.

## Adding Tests

1. Add an async function in `scale_test.py` under the FTL2 tests section
2. Add a matching playbook in `playbooks/`
3. Register both in the `TESTS` dict

Both sides should do identical work against the `scale` group/inventory.
