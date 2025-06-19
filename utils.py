import concurrent.futures
import json
import os
import os.path
import py7zr
import subprocess
import tarfile
import time
import zipfile


class Result:
    """Class of result attributes of an executed command.

    Attributes:
        command: command to be executed.
        exit_status: command's exit status.
        stdout: command's output.
        stderr: command's error.
    """
    def __init__(self, command, stdout, stderr, pid, exit_status):
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.pid = pid
        self.exit_status = exit_status

    def __repr__(self):
        return ('Result(command=%r, stdout=%r, stderr=%r, exit_status=%r)'
                ) % (self.command, self.stdout, self.stderr, self.exit_status)


def run(log, command, logfile=None, subprocess_input=""):
    """Executes a command in a subprocess and returns its process id, output,
    error and exit status.

    Commands can be either shell commands (given as strings) or the
    path and arguments to an executable (given as a list).
    This function will block until the subprocess finishes or times out.

    Args:
        log: logger instance for capturing logs
        command: command to be executed.
        logfile: command output logfile path.
        subprocess_input: Input to be given for the subprocess.

    Returns:
        result: result object of executed command, False on error.
    """
    if logfile:
        proc = subprocess.Popen(command, stdout=open(logfile, 'w+'), stderr=open(logfile, 'w+'), stdin=subprocess.PIPE,
                                shell=True)
        return proc
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)

    (out, err) = proc.communicate(timeout=600, input=subprocess_input.encode())

    result = Result(command=command, stdout=out.decode("utf-8").strip(), stderr=err.decode("utf-8").strip(),
                    pid=proc.pid, exit_status=proc.returncode)
    output = out.decode("utf-8").strip() if out else err.decode("utf-8").strip()
    log.info("Command: {}\nOutput: {}".format(command, output))
    return result


def run_async(log, command, env=None):
    """Executes shell command in the background.

    Args:
        log: logger instance for capturing logs
        command: command to be executed.
        env: run environment.

    Returns:
        proc: object of created process.
    """
    log.info("Command: {}".format(command))
    proc = subprocess.Popen(command, env=env, preexec_fn=os.setpgrp, shell=not isinstance(command, list),
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return proc


def read_json(log, file_name):
    """ Function to parse the Json file.

    Args:
        log: logger instance for capturing logs
        file_name: json file to parse.

    Returns:
        Json data in dict format.
    """
    if file_name.endswith('.json') and os.path.isfile(file_name):
        with open(file_name, 'r') as json_data:
            data = json.load(json_data)
        return data
    else:
        log.error("file is not present in the given path or file type is incorrect")


def kill_process(log, process_list):
    """ Kills the daemon process.

    Args:
        log: logger instance for capturing logs
        process_list: list of process id's.

    Returns:
        True if the processes has killed.
    """
    if len(process_list) > 0:
        for line in process_list:
            run(log, 'kill -9 {}'.format(line))
            log.info("Killed process {}".format(line))
        return True
    else:
        log.info("No processes are running")
        return True


def check_process_running(log, process):
    """ Checking the daemon processes.

    Args:
        log: logger instance for capturing logs
        process: path of daemon.

    Returns:
        Returns the list of process id's.
    """
    command = ''.join(['pidof ', process])
    output = run(log, command)
    output = output.stdout.split(' ')
    process_list = []
    for line in output:
        if line:
            process_list.append(line)
    log.debug("Processes running: {}".format(process_list))
    return process_list


def check_command_running(log, process):
    """ Checking the daemon processes.

    Args:
        log: logger instance for capturing logs
        process: path of daemon.

    Returns:
        Returns the list of process id's.
    """
    command = ''.join(['ps -o pid,cmd -e | grep ', f"\"{process}\""])
    output = run(log, command)
    output = output.stdout.split('\n')
    process_list = []
    for line in output:
        item = line.strip().split(' ')
        if "btmon" in process or "arecord" in process or "l2test" in process:
            process_list.append((item[0]))
        elif item[3] == process.split(" ")[-1].rstrip('"'):
            process_list.append((item[0]))
    log.debug("Processes running: {}".format(process_list))
    return process_list


def time_out(log, limit):
    """ Decorator to limit the execution time of a function.

    Args:
        log: logger instance for capturing logs
        limit (float): The maximum execution time limit in seconds.

    Returns:
        function: Decorator function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            if execution_time > limit:
                raise TimeoutError(f"Execution time exceeded max_limit {limit} seconds")
            log.info(f"Function '{func.__name__}' took {execution_time} seconds to execute.")
            return result
        return wrapper
    return decorator


def find_files(log, filename, search_path):
    """ Find files with a specific filename in a given directory path.

    Args:
        log: logger instance for capturing logs
        filename (str): The name of the file to search for.
        search_path (str): The directory path to search within.

    Returns:
        str: The absolute path of the found file, or None if no file was found.
    """
    # List to store the paths of found files
    result = []

    # Traverse through the directory tree starting from search_path
    for root, directory, files in os.walk(search_path):
        # Check if the filename exists in the current directory
        if filename in files:
            # Add the path of the found file to the result list
            result.append(os.path.join(root, filename))

    if len(result) == 0:
        log.error("No such file")
    else:
        log.debug("File found: {}".format(os.path.abspath(filename)))
        return os.path.abspath(filename)


def stop_subprocess(log, process):
    """ Stop a subprocess.

    Args:
        log: logger instance for capturing logs
        process (subprocess.Popen): The subprocess object to stop.
    """
    process.terminate()
    time.sleep(1)

    if process.poll() is None:
        log.error("Subprocess is still running.")
    else:
        log.info("Subprocess {} has been terminated.".format(process))


def get_subprocess_output(log, process):
    """ Get the output of a subprocess.

    Args:
        log: logger instance for capturing logs
        process (subprocess.Popen): The subprocess object.

    Returns:
        str: The output of the subprocess.

    """
    # Read the output of the subprocess
    output, error = process.communicate()

    log.info(f"This is the output of the command called in the subprocess{output.decode()}")
    log.error(error.decode())


def compress_zip(log, directory_path, format_file):
    """ Compress a directory into different formats.

    Args:
        log: logger instance for capturing logs
        directory_path (str): The path of the directory to compress.
        format_file (int): The format to use for compression.
        (1: zip, 2: tar, 3: 7z, 4: default)
    """
    if format_file == 'zip':
        output_path = f'{directory_path}.zip'
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, directory, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    dir_name = os.path.relpath(file_path, directory_path)
                    zipf.write(file_path, dir_name)

    if format_file == 'tar' or format_file == 'default':
        output_path = f'{directory_path}.tar'
        with tarfile.open(output_path, 'w') as tar:
            tar.add(directory_path), os.path.basename(directory_path)

    if format_file == '7z':
        output_path = f'{directory_path}.7z'
        with py7zr.SevenZipFile(output_path, 'w') as szf:
            szf.writeall(directory_path, os.path.basename(directory_path))


def unzip_file(log, zip_path, extract_path):
    """ Unzip a file based on its extension.

    Args:
        log: logger instance for capturing logs
        zip_path (str): The path of the ZIP file to unzip.
        extract_path (str): The path to extract the contents of the ZIP file.
    """
    valid_extensions = ['.zip', '.tar', '.7z']
    if not os.path.exists(zip_path):
        log.error("Error: File does not exist.")
        return

    ext = os.path.splitext(zip_path)[1]

    if ext in valid_extensions:
        if ext == '.zip':
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_path)

        elif ext == '.tar':
            with tarfile.open(zip_path, 'r') as tar:
                tar.extractall(extract_path)

        elif ext == '.7z':
            with py7zr.SevenZipFile(zip_path, 'r') as szf:
                szf.extractall(extract_path)
    else:
        log.error(f"Invalid file extension. Supported extensions are: {valid_extensions}")


def get_directory_size(log, directory_path):
    """ Get the size of a directory in bytes.

    Args:
        log: logger instance for capturing logs
        directory_path (str): The path of the directory.

    Returns:
        int: The size of the directory in bytes, or None if the directory does not exist.
    """

    if not os.path.exists(directory_path):
        log.error("Error: Path does not exist.\n")
        return None

    if os.path.isfile(directory_path):
        return os.path.getsize(directory_path)

    total_size = 0
    for path, directory, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(path, file_name)
            total_size += os.path.getsize(file_path)
    return total_size


def start_btmon_logger(log, logger_file):
    """Method to start the btmon_logger process.

    Args:
        log: logger instance for capturing logs.
        logger_file : log file to capture btmon logs.

    Returns:
        True, if the btmon-logger process started successfully.
        False, if the btmon-logger process failed to start.
    """
    btmon_logger_path = "/usr/local/bluez/bluez-tools/bin/btmon-logger"
    btmon_logger_command = f'{btmon_logger_path} -b {logger_file}'
    btmon_logger_process = subprocess.Popen(
        btmon_logger_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if btmon_logger_process.returncode is None:
        log.info("btmon-logger process started successfully")
        return True
    else:
        log.error("Failed to start btmon-logger process")
        return False


def kill_btmon_logger(log, logger_file):
    """Method to kill the btmon_logger process.

    Args:
        log: logger instance for capturing logs.
        logger_file: btmon log capture file.

    Returns:
        True: If the processes are killed else false.
    """
    btmon_logger_path = "/usr/local/bluez/bluez-tools/bin/btmon-logger"
    btmon_logger_command = f'{btmon_logger_path} -b {logger_file}'
    process_list = check_command_running(log, btmon_logger_command)
    if process_list:
        return kill_process(log, process_list)
    else:
        log.error("btmon process is not available")
        return False


def start_wireshark(log, duration, log_path):
    """Starts a Wireshark capture in the background and generates a pcap file to capture and save the logs.

    Args:
        log: logger instance for capturing logs.
        duration (int): Time duration in seconds for which logs should be captured.
        log_path (str): The path to the directory where the capture file should be saved.

    Returns:
        tuple or None: A tuple containing the path to the output pcap file and the process object if the capture
        started successfully. Returns None if there's an error during the process.
    """
    timestamp = time.strftime("%y%m%d_%H%M%S", time.localtime())
    output_file = f"{log_path}/capture_{timestamp}.pcap"
    cmd = ['tshark', '-i', 'nRF Sniffer for 802.15.4', '-f', 'IEEE 802.15.4 TAP', '-a', f'duration:{duration}',
           '-w', output_file]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        log.info("Wireshark capture started\n{}".format(output_file))
        return output_file, process
    except subprocess.CalledProcessError as error:
        log.error("Error starting Wireshark capture: %s", error)
        return None


def stop_wireshark(log, process):
    """Stops the Wireshark capture.

    Args:
        log: logger instance for capturing logs
        process (subprocess.Popen): The process object for the Wireshark capture.

    Returns:
        None
    """
    try:
        if process:
            process.terminate()
            process.wait()
            log.info("Wireshark(tshark) stopped")
    except Exception as e:
        log.error("Failed to stop Wireshark: %s", e)


def convert_to_little_endian(log, bd_addr):
    """ Convert the address to little endian.

    Args:
        log: logger instance for capturing logs.
        bd_addr: bd_address to be converted.

    Returns:
         It returns the converted bd_addr.
    """
    return ' '.join((bd_addr.split(":"))[::-1])


def get_hci_interface(log, bd_address):
    """ Get hci interface.

    Args:
        log: logger instance for capturing logs.
        bd_address: Address of local device.

    Returns:
        Success: It returns the hci interface.
    """
    command = "hciconfig | grep -B 1 {}".format(bd_address)
    output = run(log, command).stdout
    return output.split(":")[0]


def convert_data_to_little_endian(log, num_of_octets, data):
    """ Converts the data to little endian.

    Args:
        log (Logger): The logger object to log messages.
        num_of_octets:  Total number of significant and non-significant octets.
        data: Significant Data.

    Returns:
         It returns the converted bd_addr.
    """
    if num_of_octets * 2 > len(data):
        len_zero_octets = (num_of_octets * 2) - (len(data))
        zero_octets = ""
        for i in range(0, int(len_zero_octets)):
            zero_octets += "0"
        data = "".join([zero_octets, data])
    return " ".join(reversed([data[i:i + 2] for i in range(0, len(data), 2)]))


def integer_to_nibble_convert(value):
    """integer to nibble  convert function.

    Args:
        value:integer value

    Returns:
        Returns hex high nibble value and low nibble value
    """
    high_nibble, low_nibble = value >> 4, value & 0x0F
    return high_nibble, low_nibble


def ascii_string(string):
    """Encodes the string into ascii.

    Args:
        string: string to be encoded.

    Returns:
        Encoded string.
    """
    return str(string).encode('ASCII')


def create_threadpool(log, arg_list, timeout=60):
    """Creates threadpool for list of functions.

    Args:
        log (Logger): The logger object to log messages.
        arg_list: list of function and parameters (e.g [(func1,(args)), (func2, (args))])
        timeout: timeout duration for waiting for result.

    Returns:
        Results dictionary, False otherwise.

    """
    futures = {}
    results = {}
    counter = 0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exe:
            for arg in arg_list:
                log.debug("Starting thread for api {}".format(arg[0]))
                futures[arg[0].__name__] = exe.submit(arg[0], *arg[1])
        for future in concurrent.futures.as_completed(futures.values(), timeout=timeout):
            results[list(futures.keys())[counter]] = future.result()
            counter += 1
        return results
    except Exception as error:
        log.error("Failed to create threadpool {}".format(error))
        return False


def get_host_ip(log):
    """Returns the ip of the host system.

    Args:
        log (Logger): The logger object to log messages.

    Returns:
        IP of the host system.
    """
    return run(log, "hostname -I").stdout
