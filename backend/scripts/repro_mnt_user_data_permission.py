"""Reproduce /mnt/user-data permission issue.

Run inside container to reproduce the exact failure:
    docker exec -it deer-flow-gateway python /app/backend/scripts/repro_mnt_user_data_permission.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main():
    print(f"Running as user: {os.getuid()}:{os.getgid()}")
    print(f"User name: {os.popen('whoami').read().strip()}")

    # 1. Check /mnt/ mount
    print("\n=== /mnt/ contents ===")
    mnt = Path("/mnt")
    if mnt.exists():
        for entry in sorted(mnt.iterdir()):
            try:
                st = entry.stat()
                print(f"  {entry}  uid={st.st_uid} gid={st.st_gid} mode={oct(st.st_mode)}")
            except OSError as e:
                print(f"  {entry}  ERROR: {e}")
    else:
        print("  /mnt does not exist")

    # 2. Try to write to /mnt/user-data
    print("\n=== Test write to /mnt/user-data ===")
    test_path = Path("/mnt/user-data/test_write.txt")
    try:
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("hello from reproduction script")
        print(f"  Write succeeded: {test_path}")
        content = test_path.read_text()
        assert "hello" in content
        print(f"  Read back succeeded: {content!r}")
    except PermissionError as e:
        print(f"  PermissionError: {e}")
        return 1
    except OSError as e:
        print(f"  OSError: {e}")
        return 1

    # 3. Try to write to /mnt/user-data/workspace
    print("\n=== Test write to /mnt/user-data/workspace ===")
    workspace_path = Path("/mnt/user-data/workspace/test_workspace.txt")
    try:
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        workspace_path.write_text("hello from workspace test")
        print(f"  Write succeeded: {workspace_path}")
    except PermissionError as e:
        print(f"  PermissionError: {e}")
        return 1

    # 4. Try to write to /mnt/user-data/outputs
    print("\n=== Test write to /mnt/user-data/outputs ===")
    outputs_path = Path("/mnt/user-data/outputs/test_output.txt")
    try:
        outputs_path.parent.mkdir(parents=True, exist_ok=True)
        outputs_path.write_text("hello from outputs test")
        print(f"  Write succeeded: {outputs_path}")
    except PermissionError as e:
        print(f"  PermissionError: {e}")
        return 1

    # 5. Check what /mnt/user-data actually maps to
    print("\n=== Investigate /mnt/user-data actual path ===")
    deer_flow = Path("/app/backend/.deer-flow")
    if deer_flow.exists():
        threads_dir = deer_flow / "threads"
        if threads_dir.exists():
            for thread_dir in threads_dir.iterdir():
                user_data = thread_dir / "user-data"
                if user_data.exists():
                    try:
                        st = user_data.stat()
                        print(f"  {user_data}  uid={st.st_uid} gid={st.st_gid} mode={oct(st.st_mode)}")
                        for sub in user_data.iterdir():
                            if sub.is_dir():
                                try:
                                    sub_st = sub.stat()
                                    print(f"    {sub}  uid={sub_st.st_uid} gid={sub_st.st_gid} mode={oct(sub_st.st_mode)}")
                                except OSError as e:
                                    print(f"    {sub}  ERROR: {e}")
                    except OSError as e:
                        print(f"  {user_data}  ERROR: {e}")
        else:
            print(f"  {threads_dir} does not exist")
    else:
        print(f"  {deer_flow} does not exist")

    # 6. Check current working dir
    print("\n=== Current working dir ===")
    print(f"  cwd: {os.getcwd()}")
    print(f"  DEER_FLOW_HOME: {os.environ.get('DEER_FLOW_HOME', 'NOT SET')}")

    print("\n=== Reproduction complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
