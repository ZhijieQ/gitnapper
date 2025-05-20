from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import argparse
import os
import logging
import sys
import utils

# Logging options
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname).4s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Argument parsing
parser = argparse.ArgumentParser(
    prog="inplace_encrypter",
    description="Background process that analyzes files for sudden entropy spikes",
)

parser.add_argument(
    "-w",
    "--workdir",
    default=None,
    help="The directory where the process will look for files to analyze. Defaults to the current working directory.",
)
parser.add_argument(
    "-r",
    "--recursion-level",
    type=int,
    default=0,
    help="The level of recursion for searching subdirectories. Default is 0 (only the specified directory).",
)
args = parser.parse_args()

# Main program

blocked_directories = ["/", ".", "~", ".."]

if not args.workdir:
    logging.warning(
        f"Use -w [WORKDIR] to specify a directory. Be {utils.red('very')} careful!"
    )
    exit(-1)
if args.workdir in blocked_directories:
    logging.error(
        f"Try a different directory, encrypting data in {utils.red(args.workdir)} is dangerous!"
    )
    exit(-1)

logging.info(
    f"Naive overwrite encryption: working on directory {utils.green(args.workdir)} at recursion level {utils.green(args.recursion_level)}"
)
key = os.urandom(32)
iv = os.urandom(16)
cipher = Cipher(algorithms.AES(key), modes.CBC(iv))

for file in utils.allfiles(
    path=os.path.abspath(args.workdir),
    recursion_level=args.recursion_level,
    ignored=[".git", "node_modules", ".vscode", "venv"],
):

    with open(file, "rb") as f:
        data = f.read()

    padder = padding.PKCS7(256).padder()
    padded_data = padder.update(data) + padder.finalize()

    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()

    with open(file, "wb") as f:
        f.write(ct)

logging.info(f"Encryption finished.\nPassword: {key.hex()}\nIV: {iv.hex()}")