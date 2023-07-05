import os
import argparse
import configparser

def valid_readable_file(path):
    # https://github.com/DCAN-Labs/CABINET/blob/main/src/utilities.py
    """
    Throw exception unless parameter is a valid readable filepath string. Use
    this, not argparse.FileType("r") which leaves an open file handle.
    :param path: Parameter to check if it represents a valid filepath
    :return: String representing a valid filepath
    """
    return validate(path, lambda x: os.access(x, os.R_OK),
                    os.path.abspath, "Cannot read file at '{}'")

def validate(to_validate, is_real, make_valid, err_msg, prepare=None):
    # https://github.com/DCAN-Labs/CABINET/blob/main/src/utilities.py
    """
    Parent/base function used by different type validation functions. Raises an
    argparse.ArgumentTypeError if the input object is somehow invalid.
    :param to_validate: String to check if it represents a valid object 
    :param is_real: Function which returns true iff to_validate is real
    :param make_valid: Function which returns a fully validated object
    :param err_msg: String to show to user to tell them what is invalid
    :param prepare: Function to run before validation
    :return: to_validate, but fully validated
    """
    try:
        if prepare:
            prepare(to_validate)
        assert is_real(to_validate)
        return make_valid(to_validate)
    except (OSError, TypeError, AssertionError, ValueError,
            argparse.ArgumentTypeError):
        raise argparse.ArgumentTypeError(err_msg.format(to_validate))

def valid_config_parameter(config_file, section, parameter):
    config = configparser.ConfigParser()
    try:
        with open(config_file) as f:
            config.read_file(f)
    except IOError:
        raise FileNotFoundError(
            f"Config file ({config_file}) not found. Add or rename file so {config_file} exists in directory."
        )

    # check config information is available, and connect to the databse selected
    if config.has_option(section, parameter):
        return config.get(section, parameter)
    else: 
        raise NameError(f"Parameter {parameter} does not exist in section {section} in the config file {config_file}")

class Directory:
    def __init__(self, directory):
        if not os.path.isdir(directory):
            os.makedirs(directory)
        self.directory = directory
    
    def __str__(self) -> str:
        return self.directory

class DataSource:
    def __init__(self, source):
        valid_sources = ["redcap", "qualtrics"]
        if source in valid_sources:
            self.source = source
        else:
            raise argparse.ArgumentTypeError("{} is not a valid datasource. Please choose from {}".format(source, valid_sources))
    def __str__(self) -> str:
        return self.source
