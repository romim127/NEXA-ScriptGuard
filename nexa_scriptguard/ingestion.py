import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .limits import ScanLimits


class InputError(ValueError):
    pass


class OutputError(OSError):
    pass


@dataclass(frozen=True)
class Source:
    path: Path
    data: bytes
    device: int
    inode: int


def read_source(path: Path, limits: ScanLimits) -> Source:
    try:
        resolved = path.expanduser().resolve(strict=True)
        before = resolved.stat()
        if not stat.S_ISREG(before.st_mode):
            raise InputError("Input must be a regular file")
        if before.st_size > limits.max_input_bytes:
            raise InputError(
                f"Input exceeds the {limits.max_input_bytes}-byte limit"
            )
        with resolved.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise InputError("Input changed while it was being opened")
            data = stream.read(limits.max_input_bytes + 1)
            after = os.fstat(stream.fileno())
        if len(data) > limits.max_input_bytes:
            raise InputError(
                f"Input exceeds the {limits.max_input_bytes}-byte limit"
            )
        if (opened.st_size, opened.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ):
            raise InputError("Input changed while it was being read")
        return Source(resolved, data, opened.st_dev, opened.st_ino)
    except InputError:
        raise
    except OSError as exc:
        raise InputError(f"Unable to read input: {exc}") from exc


def _identity(path: Path):
    try:
        info = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    return info.st_dev, info.st_ino


def _destination(path: Path) -> Path:
    parent = path.expanduser().parent.resolve(strict=True)
    return parent / path.name


def _check_destinations(paths, source: Source):
    destinations = []
    seen = set()
    source_identity = (source.device, source.inode)
    for path in paths:
        destination = _destination(path)
        key = os.path.normcase(str(destination))
        if key in seen:
            raise OutputError(f"Duplicate report destination: {destination}")
        seen.add(key)
        identity = _identity(destination)
        if destination.is_symlink():
            raise OutputError(f"Refusing symbolic-link output: {destination}")
        if identity is not None:
            if identity == source_identity:
                raise OutputError(
                    f"Report destination is the analyzed input: {destination}"
                )
            raise OutputError(f"Refusing to overwrite existing output: {destination}")
        destinations.append(destination)
    return destinations


def write_reports(outputs: dict[Path, bytes], source: Source, limits: ScanLimits):
    """Stage outputs, then atomically create new names without replacing existing files."""
    destinations = _check_destinations(list(outputs), source)
    staged = []
    published = []
    cleanup_errors = []
    try:
        for destination, content in zip(destinations, outputs.values()):
            if len(content) > limits.max_output_bytes:
                raise OutputError(
                    f"Report exceeds the {limits.max_output_bytes}-byte limit"
                )
            fd, name = tempfile.mkstemp(
                prefix=".nexa-", suffix=".tmp", dir=str(destination.parent)
            )
            temporary = Path(name)
            staged.append((temporary, destination))
            try:
                if hasattr(os, "fchmod"):
                    os.fchmod(fd, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
        for temporary, destination in staged:
            os.link(temporary, destination)
            published.append(destination)
        if os.name != "nt":
            for parent in {destination.parent for destination in destinations}:
                directory_fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
    except Exception as exc:
        rollback_errors = []
        for temporary, destination in reversed(staged):
            if destination not in published:
                continue
            try:
                if _identity(destination) == _identity(temporary):
                    destination.unlink()
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        detail = f"Report publication failed: {exc}"
        if published:
            detail += "; previously published outputs were rolled back where possible"
        if rollback_errors:
            detail += "; rollback errors: " + "; ".join(rollback_errors)
        if isinstance(exc, OSError):
            raise OutputError(detail) from exc
        raise
    finally:
        for temporary, _ in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as exc:
                cleanup_errors.append(f"{temporary}: {exc}")
        if cleanup_errors:
            raise OutputError(
                "Unable to remove staged report files: " + "; ".join(cleanup_errors)
            )
