from apt_select import constant as constant

def utf8_decode(encoded: bytes) -> str: ...

class URLGetTextError(Exception): ...

def get_text(url: str, timeout_sec: float = ...) -> str: ...
def progress_msg(processed: float | int, total: float | int) -> None: ...