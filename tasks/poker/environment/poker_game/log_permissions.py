"""Keep resumed agent logs writable after Harbor transfers ownership to the host."""

import errno
import os
import stat
from pathlib import Path


def restore_agent_log_access(path: Path, agent_gid: int) -> None:
    """Grant the agent group access without changing the host owner."""
    try:
        root_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return
    try:
        for _, _, files, directory_fd in os.fwalk(".", dir_fd=root_fd, follow_symlinks=False):
            mode = os.fstat(directory_fd).st_mode & 0o777
            os.fchown(directory_fd, -1, agent_gid)
            os.fchmod(directory_fd, mode | 0o070)
            for name in files:
                try:
                    entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1:
                        continue
                    fd = os.open(
                        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd
                    )
                except OSError as exc:
                    if exc.errno in (errno.ELOOP, errno.ENOENT):
                        continue
                    raise
                try:
                    info = os.fstat(fd)
                    if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                        os.fchown(fd, -1, agent_gid)
                        os.fchmod(fd, (info.st_mode & 0o777) | 0o060)
                finally:
                    os.close(fd)
    finally:
        os.close(root_fd)
