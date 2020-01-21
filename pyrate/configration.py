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


class Configration():
    def __init__(self, config_file_path):

        parser = ConfigParser()
        parser.optionxform = str
        # mimic header to fulfil the requirement for configparser
        with open(config_file_path) as stream:
            parser.read_string("[root]\n" + stream.read())

        for key, value in parser._sections["root"].items():
            self.__dict__[key] = value

        # check if required values are supplied
        if not set(PYRATE_DEFAULT_CONFIGRATION).issubset(self.__dict__):
            raise ValueError("Required configration parameters: " + str(set(PYRATE_DEFAULT_CONFIGRATION).difference(self.__dict__)) + " are missing from input config file.")

if __name__ == "__main__":
    config_file_path = "C:\\Users\\sheec\\Desktop\\Projects\\PyRate\\sample_data\\input_parameters.conf"
    config = Configration(config_file_path)
    print(set(PYRATE_DEFAULT_CONFIGRATION))
    print(config.__dict__)



