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
This Python module contains tools for reading ROI_PAC format input data.
"""
import os
import re
import datetime

import constants
from constants import WIDTH, FILE_LENGTH, X_FIRST, X_STEP, Y_FIRST, Y_STEP, WAVELENGTH, DATE, DATE12, Z_SCALE, \
    PROJECTION, DATUM, X_LAST, Y_LAST, RADIANS, ROIPAC, INT_HEADERS, STR_HEADERS, FLOAT_HEADERS, DATE_HEADERS, \
    ROI_PAC_HEADER_FILE_EXT
from core import config as cf


def parse_date(dstr):
    """
    Parses ROI_PAC 'yymmdd' or 'yymmdd-yymmdd' format string to datetime.

    :param str dstr: 'date' or 'date1-date2' string

    :return: dstr: datetime string or tuple
    :rtype: str or tuple
    """
    def to_date(date_str):
        """convert string to datetime"""
        year, month, day = [int(date_str[i:i+2]) for i in range(0, 6, 2)]
        year += 1900 if ((year <= 99) and (year >= 50)) else 2000
        return datetime.date(year, month, day)

    if "-" in dstr:  # ranged date
        return tuple([to_date(d) for d in dstr.split("-")])
    else:
        return to_date(dstr)


def parse_header(hdr_file):
    """
    Parses ROI_PAC header file metadata to a dictionary.

    :param str hdr_file: `path to ROI_PAC *.rsc file`

    :return: subset: subset of metadata
    :rtype: dict
    """
    with open(hdr_file) as f:
        text = f.read()

    try:
        lines = [e.split() for e in text.split("\n") if e != ""]
        headers = dict(lines)
        is_dem = True if DATUM in headers or Z_SCALE in headers \
                         or PROJECTION in headers else False
        if is_dem and DATUM not in headers:
            msg = 'No "DATUM" parameter in DEM header/resource file'
            raise RoipacException(msg)
    except ValueError:
        msg = "Unable to parse content of %s. Is it a ROIPAC header file?"
        raise RoipacException(msg % hdr_file)

    for k in headers.keys():
        if k in INT_HEADERS:
            headers[k] = int(headers[k])
        elif k in STR_HEADERS:
            headers[k] = str(headers[k])
        elif k in FLOAT_HEADERS:
            headers[k] = float(headers[k])
        elif k in DATE_HEADERS:
            headers[k] = parse_date(headers[k])
        else:  # pragma: no cover
            pass  # ignore other headers

    # grab a subset for GeoTIFF conversion
    subset = {constants.PYRATE_NCOLS: headers[WIDTH],
              constants.PYRATE_NROWS: headers[FILE_LENGTH],
              constants.PYRATE_LAT: headers[Y_FIRST],
              constants.PYRATE_LONG: headers[X_FIRST],
              constants.PYRATE_X_STEP: headers[X_STEP],
              constants.PYRATE_Y_STEP: headers[Y_STEP]}

    if is_dem:
        subset[constants.PYRATE_DATUM] = headers[DATUM]
    else:
        subset[constants.PYRATE_WAVELENGTH_METRES] = headers[WAVELENGTH]

        # grab master/slave dates from header, or the filename
        has_dates = True if DATE in headers and DATE12 in headers else False
        dates = headers[DATE12] if has_dates else _parse_dates_from(hdr_file)
        subset[constants.MASTER_DATE], subset[constants.SLAVE_DATE] = dates

        # replace time span as ROIPAC is ~4 hours different to (slave - master)
        timespan = (subset[constants.SLAVE_DATE] - subset[constants.MASTER_DATE]).days / constants.DAYS_PER_YEAR
        subset[constants.PYRATE_TIME_SPAN] = timespan

        # Add data units of interferogram
        subset[constants.DATA_UNITS] = RADIANS

    # Add InSAR processor flag
    subset[constants.PYRATE_INSAR_PROCESSOR] = ROIPAC

    # add custom X|Y_LAST for convenience
    subset[X_LAST] = headers[X_FIRST] + (headers[X_STEP] * (headers[WIDTH]))
    subset[Y_LAST] = headers[Y_FIRST] + (headers[Y_STEP] * (headers[FILE_LENGTH]))

    return subset


def _parse_dates_from(filename):
    """Determine dates from file name"""
    # pylint: disable=invalid-name
    # process dates from filename if rsc file doesn't have them (skip for DEMs)
    p = re.compile(r'\d{6}-\d{6}')  # match 2 sets of 6 digits separated by '-'
    m = p.search(filename)

    if m:
        s = m.group()
        min_date_len = 13  # assumes "nnnnnn-nnnnnn" format
        if len(s) == min_date_len:
            return parse_date(s)
    else:  # pragma: no cover
        msg = "Filename does not include master/slave dates: %s"
        raise RoipacException(msg % filename)


def manage_header(header_file, projection):
    """
    Manage header files for ROI_PAC interferograms and DEM files.
    NB: projection = roipac.parse_header(dem_file)[ifc.PYRATE_DATUM]

    :param str header_file: `ROI_PAC *.rsc header file path`
    :param projection: Projection obtained from dem header.

    :return: combined_header: Combined metadata dictionary
    :rtype: dict
    """

    header = parse_header(header_file)
    if constants.PYRATE_DATUM not in header:  # DEM already has DATUM
        header[constants.PYRATE_DATUM] = projection
    header[constants.DATA_TYPE] = constants.ORIG  # non-cropped, non-multilooked geotiff
    return header


def roipac_header(file_path, params):
    """
    Function to obtain a header for roipac interferogram file or converted
    geotiff.
    """
    rsc_file = os.path.join(params[cf.DEM_HEADER_FILE])
    if rsc_file is not None:
        projection = parse_header(rsc_file)[constants.PYRATE_DATUM]
    else:
        raise RoipacException('No DEM resource/header file is '
                                     'provided')
    if file_path.endswith('_dem.tif'):
        header_file = os.path.join(params[cf.DEM_HEADER_FILE])
    elif file_path.endswith('_unw.tif'):
        base_file = file_path[:-8]
        header_file = base_file + '.unw.' + ROI_PAC_HEADER_FILE_EXT
    else:
        header_file = "%s.%s" % (file_path, ROI_PAC_HEADER_FILE_EXT)

    header = manage_header(header_file, projection)

    return header


class RoipacException(Exception):
    """
    Convenience class for throwing exception
    """
