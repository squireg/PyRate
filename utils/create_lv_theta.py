# This Python module is part of the PyRate software package
#
# Copyright 2017 Geoscience Australia
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
'''
This is used to create the dummy incidence map file .inc file
This is used to create the dummy elevation map file .lv_theta file
'''

import os

import numpy as np
from osgeo import gdal
from osgeo import osr
from osgeo import ogr
from osgeo import gdalconst
from osgeo import gdal_array

import constants
from core import shared, gamma
import common

elevation_file = os.path.join(common.SML_TEST_GAMMA,
                              os.path.splitext(common.SML_TEST_DEM_GAMMA)[0]
                              + '.lv_theta')

inc_file = os.path.join(common.SML_TEST_GAMMA,
                        os.path.splitext(common.SML_TEST_DEM_GAMMA)[0]
                        + '.inc')

dest_lv_theta = os.path.splitext(elevation_file)[0] + '_lv_theta.tif'
dest_inc = os.path.splitext(elevation_file)[0] + '_inc.tif'

dem_header_file = common.SML_TEST_DEM_HDR_GAMMA

dem_header = gamma.parse_dem_header(dem_header_file)

header = gamma.parse_epoch_header(
    os.path.join(common.SML_TEST_GAMMA, '20060828_slc.par'))


incidence_angle = header[constants.PYRATE_INCIDENCE_DEGREES]
incidence_data = np.ones(shape=(dem_header[constants.PYRATE_NROWS],
                                dem_header[constants.PYRATE_NCOLS])
                         ) * incidence_angle

elevation_data = np.ones(shape=(dem_header[constants.PYRATE_NROWS],
                                dem_header[constants.PYRATE_NCOLS])
                         ) * (90.0 - incidence_angle)

shared.write_unw_from_data_or_geotiff(geotif_or_data=incidence_data,
                                      dest_unw=inc_file,
                                      ifg_proc=1)

shared.write_unw_from_data_or_geotiff(geotif_or_data=elevation_data,
                                      dest_unw=elevation_file,
                                      ifg_proc=1)

header.update(dem_header)
header[constants.PYRATE_TIME_SPAN] = 0
header[constants.SLAVE_DATE] = 0
header[constants.DATA_UNITS] = 'degrees'
header[constants.DATA_TYPE] = constants.INCIDENCE
header[constants.SLAVE_TIME] = 0
shared.write_geotiff(header=header, data_path=elevation_file,
                     dest=dest_lv_theta, nodata=np.nan)

shared.write_geotiff(header=header, data_path=inc_file,
                     dest=dest_inc, nodata=np.nan)


ds = gdal.Open(dest_lv_theta, gdal.GA_ReadOnly)
data_elevation = ds.ReadAsArray()
ds = None


ds = gdal.Open(dest_inc, gdal.GA_ReadOnly)
data_inc = ds.ReadAsArray()
ds = None

np.testing.assert_array_almost_equal(90 - incidence_data, data_elevation,
                                     decimal=4)
np.testing.assert_array_almost_equal(incidence_data, data_inc,
                                     decimal=4)
