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
"""
This Python module contains functions to control PyRate log outputs
"""
import os
import logging
from core.mpiops import size, rank


PYRATEPATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_setting_file = os.path.join(PYRATEPATH, "log_settings.txt")

with open(log_setting_file, "r") as myfile:
    log_level = myfile.readlines()[0].strip()

pyratelogger = logging.getLogger(__name__)
pyratelogger.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s %(module)s %(lineno)d %(process)d " + str(rank) + "/" + str(size-1)+" %(message)s", "%H:%M:%S")

ch = logging.StreamHandler()
ch.setLevel(log_level)
ch.setFormatter(formatter)


fh = logging.FileHandler('pyrate.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

pyratelogger.addHandler(ch)
pyratelogger.addHandler(fh)

