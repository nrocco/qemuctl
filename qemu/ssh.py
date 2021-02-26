import logging
import subprocess


def Ssh(host, command, cwd=None):
    command = ["ssh", host, "--"] + command
    logging.debug(f">>> {command}")
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    logging.debug(f"<<< stdout: {result.stdout.strip()}")
    logging.debug(f"<<< stderr: {result.stderr.strip()}")
    result.check_returncode()
    return result
