import logging
import subprocess


def Ssh(host, command, **kwargs):
    command = ["ssh", host, "--"] + command
    logging.debug(f">>> {command}")
    result = subprocess.run(command, text=True, capture_output=True, **kwargs)
    logging.debug(f"<<< stdout: {result.stdout.strip()}")
    logging.debug(f"<<< stderr: {result.stderr.strip()}")
    result.check_returncode()
    return result
