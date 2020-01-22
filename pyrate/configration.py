#   This Python module is part of the PyRate software package.
#
#   Copyright 2020 Geoscience Australia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from configparser import ConfigParser
from default_parameters import PYRATE_DEFAULT_CONFIGRATION
import pathlib


def set_parameter_value(data_type, input_value, default_value, required, input_name):
    if len(input_value) < 1:
        input_value = None
        if required:
            raise ValueError("A required parameter is missing value in input configuration file: "+str(input_name))

    if input_value is not None:
        if str(data_type) in "path":
            return pathlib.Path(input_value)
        return data_type(input_value)
    return default_value


def validate_parameter_value(input_name, input_value, min_value=None, max_value=None, possible_values=None):
    if isinstance(input_value, pathlib.PurePath):
        if input_name in "outdir":
            input_value = input_value.parents[0]
        if not pathlib.Path.exists(input_value):
            raise ValueError("Given path: " + str(input_value) + " dose not exist.")
    if min_value is not None:
        if input_value < min_value:
            raise ValueError("Invalid value for "+input_name+" supplied: "+input_value+". Please provided a valid value greater than "+min_value+".")
    if max_value is not None:
        if input_value > max_value:
            raise ValueError("Invalid value for "+input_name+" supplied: "+input_value+". Please provided a valid value less than "+max_value+".")

    if possible_values is not None:
        if input_value not in possible_values:
            raise ValueError("Invalid value for " + input_name + " supplied: " + input_value + ". Please provided a valid value from with in: " + str(possible_values) + ".")
    return True

def validate_file_list_values(dir, fileList):

    if dir is None:
        raise ValueError("No value supplied for input directory: "+ str(dir))
    if fileList is None:
        raise ValueError("No value supplied for input file list: " + str(fileList))

    for path_str in fileList.read_text().split('\n'):
        # ignore empty lines in file
        if len(path_str) > 1:
            if not pathlib.Path.exists(dir/path_str):
                raise ValueError("Give file name: " + path_str +" dose not exist at: " + dir)


class Configration():
    def __init__(self, config_file_path):

        parser = ConfigParser()
        parser.optionxform = str
        # mimic header to fulfil the requirement for configparser
        with open(config_file_path) as stream:
            parser.read_string("[root]\n" + stream.read())

        for key, value in parser._sections["root"].items():
            self.__dict__[key] = value

        # Validate required parameters exist.
        if not set(PYRATE_DEFAULT_CONFIGRATION).issubset(self.__dict__):
            raise ValueError("Required configuration parameters: " + str(set(PYRATE_DEFAULT_CONFIGRATION).difference(self.__dict__)) + " are missing from input config file.")

        # handle control parameters
        for parameter_name in PYRATE_DEFAULT_CONFIGRATION:
            self.__dict__[parameter_name] = set_parameter_value(PYRATE_DEFAULT_CONFIGRATION[parameter_name]["DataType"], self.__dict__[parameter_name], PYRATE_DEFAULT_CONFIGRATION[parameter_name]["DefaultValue"], PYRATE_DEFAULT_CONFIGRATION[parameter_name]["Required"], parameter_name)
            validate_parameter_value(parameter_name, self.__dict__[parameter_name], PYRATE_DEFAULT_CONFIGRATION[parameter_name]["MinValue"], PYRATE_DEFAULT_CONFIGRATION[parameter_name]["MaxValue"], PYRATE_DEFAULT_CONFIGRATION[parameter_name]["PossibleValues"])

        # Validate file names supplied in list exist.
        validate_file_list_values(self.obsdir, self.ifgfilelist)
        validate_file_list_values(self.slcFileDir, self.slcfilelist)
        if self.cohfiledir is not None or self.cohfilelist is not None:
            validate_file_list_values(self.cohfiledir, self.cohfilelist)
            
if __name__ == "__main__":
    config_file_path = "C:\\Users\\sheec\\Desktop\\Projects\\PyRate\\sample_data\\input_parameters.conf"
    config = Configration(config_file_path)
    print(config.__dict__)



