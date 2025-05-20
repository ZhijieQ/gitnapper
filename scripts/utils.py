import math
import os
from collections import Counter


BOLD = "\033[1m"
END = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"

def red(text: str):
    """Prints a bolded red version of TEXT"""
    return f"{BOLD}{RED}{text}{END}{END}"


def green(text: str):
    """Prints a bolded green version of TEXT"""
    return f"{BOLD}{GREEN}{text}{END}{END}"


def entropy(bytecount: Counter):
    """
    Computes the entropy value of a byte count, which ranges in 0 to 8 bits per byte.

    Args:
        bytecount (str): Frequency of each byte value.

    Returns:
        float: Entropy value.
    """
    value = 0
    size = sum(bytecount.values())

    for count in bytecount.values():
        p = count / size
        value -= p * math.log2(p)

    return value

def bytecount(path: str):
    """
    Returns the bytecount of a file.

    Args:
        path (str): File location

    Returns:
        float: Byte frecuency.
    """
    with open(path, "rb") as f:
        return Counter(f.read())

def allfiles(path: str, recursion_level: int, ignored: list):
    """
    Obtains all file paths derived from PATH.

    Args:
        path (str): Working directory path.
        recursion_level (int): Maximum recursion depth.
        ignored (list): List of ignored directories or files.

    Returns:
        list: Files in the directory.
    """
    fnames = [f for f in os.listdir(path) if f not in ignored]
    files = []
    if recursion_level < 0:
        return files

    for fname in fnames:
        fpath = f"{path}/{fname}"
        if os.path.isdir(fpath):
            files += allfiles(fpath, recursion_level - 1, ignored)
        elif os.path.isfile(fpath):
            files.append(fpath)

    return files

def group_by_dir(files: list):
    """
    Groups all files in a list according to their parent directory.
    """
    directories = {os.path.dirname(file): [] for file in files}

    for file in files:
        directories[os.path.dirname(file)].append(file)

    return directories
