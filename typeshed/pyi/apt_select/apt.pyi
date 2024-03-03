from _typeshed import Incomplete
from apt_select import constant as constant, utility as utility

SUPPORTED_KERNEL: str
SUPPORTED_DISTRIBUTION_TYPE: str
UNAME: str
KERNEL_COMMAND: Incomplete
MACHINE_COMMAND: Incomplete
RELEASE_COMMAND: Incomplete
RELEASE_FILE: str
LAUNCHPAD_ARCH_32: str
LAUNCHPAD_ARCH_64: str
LAUNCHPAD_ARCHES: Incomplete

class System:
    dist: Incomplete
    codename: Incomplete
    arch: Incomplete
    def __init__(self) -> None: ...

class SourcesFileError(Exception): ...

class Sources:
    DEB_SCHEMES: Incomplete
    PROTOCOLS: Incomplete
    DIRECTORY: str
    LIST_FILE: str
    urls: Incomplete
    skip_gen_msg: str
    new_file_path: Incomplete
    def __init__(self, codename: str) -> None: ...
    def set_current_archives(self) -> None: ...
    def generate_new_config(self, work_dir: str, new_mirror: str) -> None: ...
