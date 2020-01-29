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
This Python script applies optional multilooking and cropping to input
interferogram geotiff files.
"""
# -*- coding: utf-8 -*-
import logging
import os
import numpy as np
import multiprocessing
from prepifg.utilities import prepare_ifg
from core import config as cf
from osgeo import gdal, osr
from core.config import IFG_LKSX, IFG_LKSY, IFG_CROP_OPT
from constants import ALREADY_SAME_SIZE
from constants import NO_OF_PARALLEL_PROCESSES, LOW_FLOAT32
from osgeo import gdalconst
import numexpr as ne
import shutil

log = logging.getLogger(__name__)


def get_raster_extent(raster_path):
    # scr: https://gis4programmers.wordpress.com/2017/01/06/using-gdal-to-get-raster-extent/
    raster = gdal.Open(raster_path)

    upx, xres, xskew, upy, yskew, yres = raster.GetGeoTransform()

    cols = raster.RasterXSize
    rows = raster.RasterYSize

    ulx = upx + 0 * xres + 0 * xskew
    uly = upy + 0 * yskew + 0 * yres

    lrx = upx + cols * xres + rows * xskew
    lry = upy + cols * yskew + rows * yres

    raster = None
    del raster
    return [ulx, lry, lrx, uly]


def main(params, config):
    """
    Main workflow function for preparing interferograms for PyRate.

    :param dict params: Parameters dictionary read in from the config file
    """

    list_of_files_to_process = []
    list_of_files_to_process.extend(config.interferogram_files)

    # optional DEM conversion
    if params[cf.DEM_FILE] is not None:
        list_of_files_to_process.append(params["dem_file_path"])

    log.info("Preparing interferograms by cropping/multilooking")

    for file_to_process in list_of_files_to_process:
        if not os.path.isfile(file_to_process.converted_path):
            raise Exception("Cannot find geotiff: " + str(file_to_process.converted_path) + ". Ensure you have converted your interferograms to geotiffs.")

    extent = [params[cf.IFG_XFIRST], params[cf.IFG_YFIRST], params[cf.IFG_XLAST], params[cf.IFG_YLAST]]

    if not all(extent):
        extent = [180, 180, 180, 180]
        
    for file_to_process in list_of_files_to_process:
        raster_extent = get_raster_extent(file_to_process.converted_path)

        # upper left x
        if raster_extent[0] < extent[0]:
            extent[0] = raster_extent[0]
        # lower right y
        if raster_extent[1] < extent[1]:
            extent[1] = raster_extent[1]
        # lower right x
        if raster_extent[2] < extent[2]:
            extent[2] = raster_extent[2]
        # upper left y
        if raster_extent[3] < extent[3]:
            extent[3] = raster_extent[3]

    params[cf.PARALLEL] = False
    log.debug("Running using parallel processing.")
    # Init multiprocessing.Pool()
    pool = multiprocessing.Pool(NO_OF_PARALLEL_PROCESSES)

    # Running pools to convert gamma file to GeoTIFF
    pool.map(_prepifg_multiprocessing, [(file_to_process, extent, params) for file_to_process in list_of_files_to_process])

    # Closing pools
    pool.close()


def _prepifg_multiprocessing(parameters):
    """
    Multiprocessing wrapper for prepifg
    """
    raster_file, extent, params = parameters
    xlooks = params[IFG_LKSX]
    ylooks = params[IFG_LKSY]
    crop_opt = params[IFG_CROP_OPT]
    thresh = params[cf.NO_DATA_AVERAGING_THRESHOLD]

    # # If we're performing coherence masking, find the coherence file for this IFG.
    # # TODO: Refactor _is_interferogram to be unprotected (remove '_')

    if params[cf.COH_MASK] and params["cohfiledir"] is not None and params["cohfilelist"] is not None:
        coherence_path = cf.coherence_paths_for(raster_file, params, tif=True)[0]
        coherence_thresh = params[cf.COH_THRESH]
    else:
        log.debug("Coherence not set.")
        coherence_path = None
        coherence_thresh = None

    do_multilook = xlooks > 1 or ylooks > 1
    # resolution=None completes faster for non-multilooked layers in gdalwarp
    resolution = [None, None]
    raster = gdal.Open(raster_file.converted_path)
    log.debug("raster.data_path: " + str(raster))

    if do_multilook:
        log.debug("Multi-look enabled.")
        resolution = [xlooks * raster.x_step, ylooks * raster.y_step]

    if not do_multilook and crop_opt == ALREADY_SAME_SIZE:

        log.debug("xlooks: " + str(xlooks))
        log.debug("crop_opt: " + str(crop_opt))
        log.debug("renamed_path: " + str(raster_file.sampled_path))

        log.debug("Multi-look disabled and raster already of same size.")
        # TODO set metadata: {constants.DATA_TYPE: constants.MULTILOOKED} before copying
        shutil.copy(raster_file.converted_path, raster_file.sampled_path)

    if xlooks != ylooks:
        raise ValueError('X and Y looks mismatch')

    driver_type = 'GTiff'
    input_tif = raster_file.converted_path
    extent = extent
    new_res = resolution
    output_file = raster_file.sampled_path
    thresh = thresh
    out_driver_type = driver_type
    coherence_path = coherence_path
    coherence_thresh = coherence_thresh
    match_pyrate = False

    dst_ds, _, _, _ = _crop_resample_setup(extent, input_tif, new_res, output_file, out_bands=2, dst_driver_type='MEM')

    # make a temporary copy of the dst_ds for PyRate style prepifg
    tmp_ds = gdal.GetDriverByName('MEM').CreateCopy('', dst_ds) if (match_pyrate and new_res[0]) else None

    src_ds, src_ds_mem = _setup_source(input_tif)

    if coherence_path is not None and coherence_thresh is not None:
        coherence_raster = gdal.Open(coherence_path)
        coherence_masking(src_ds_mem, coherence_raster, coherence_thresh)
        del coherence_raster
        coherence_raster = None
    elif coherence_path is not None:
        raise ValueError("Coherence file provided without a coherence threshold. Please ensure you provide 'cohthresh' in your config if coherence masking is enabled.")
    elif coherence_thresh is not None:
        raise ValueError("Coherence thresh is set but path to coherence file is not supplied in input configuration.")

    resampled_average, src_ds_mem = gdal_average(dst_ds, src_ds, src_ds_mem, thresh)
    src_dtype = src_ds_mem.GetRasterBand(1).DataType
    src_gt = src_ds_mem.GetGeoTransform()

    # required to match Legacy output
    if tmp_ds:
        _alignment(input_tif, new_res, resampled_average, src_ds_mem, +src_gt, tmp_ds)

    # grab metadata from existing geotiff
    gt = dst_ds.GetGeoTransform()
    wkt = dst_ds.GetProjection()

    md = dst_ds.GetMetadata()

    # In-memory GDAL driver doesn't support compression so turn it off.
    creation_opts = ['compress=packbits'] if out_driver_type != 'MEM' else []
    out_ds = gdal_dataset(output_file, dst_ds.RasterXSize, dst_ds.RasterYSize, driver=out_driver_type, bands=1, dtype=src_dtype, metadata=md, crs=wkt, geotransform=gt, creation_opts=creation_opts)

    write_geotiff(resampled_average, out_ds, np.nan)
    log.debug("Writing geotiff: "+str(out_ds))


def _crop_resample_setup(extents, input_tif, new_res, output_file, dst_driver_type='GTiff', out_bands=2):
    """
    Convenience function for crop/resample setup
    """
    # Source
    src_ds = gdal.Open(input_tif, gdalconst.GA_ReadOnly)
    src_proj = src_ds.GetProjection()

    # source metadata to be copied into the output
    meta_data = src_ds.GetMetadata()

    # get the image extents
    min_x, min_y, max_x, max_y = extents
    print(extents)
    geo_transform = src_ds.GetGeoTransform()  # tuple of 6 numbers

    # Create a new geotransform for the image
    gt2 = list(geo_transform)
    gt2[0] = min_x
    gt2[3] = max_y
    # We want a section of source that matches this:
    resampled_proj = src_proj
    if new_res[0]:  # if new_res is not None, it can't be zero either
        resampled_geotrans = gt2[:1] + [new_res[0]] + gt2[2:-1] + [new_res[1]]
    else:
        resampled_geotrans = gt2

    px_height, px_width = _gdalwarp_width_and_height(max_x, max_y, min_x, min_y, resampled_geotrans)

    # Output / destination
    dst = gdal.GetDriverByName(dst_driver_type).Create(output_file, px_width, px_height, out_bands, gdalconst.GDT_Float32)
    dst.SetGeoTransform(resampled_geotrans)
    dst.SetProjection(resampled_proj)

    for k, v in meta_data.items():
        dst.SetMetadataItem(k, v)

    return dst, resampled_proj, src_ds, src_proj

def _gdalwarp_width_and_height(max_x, max_y, min_x, min_y, geo_trans):
    """
    Modify pixel height and width
    """
    # modified image extents
    ul_x, ul_y = world_to_pixel(geo_trans, min_x, max_y)
    lr_x, lr_y = world_to_pixel(geo_trans, max_x, min_y)
    # Calculate the pixel size of the new image
    px_width = int(lr_x - ul_x)
    px_height = int(lr_y - ul_y)
    return px_height, px_width  # this is the same as `gdalwarp`

def world_to_pixel(geo_transform, x, y):
    """
    Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
    the pixel location of a geospatial coordinate;
    see: http://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html

    :param list geo_transform: Affine transformation coefficients
    :param float x: longitude coordinate
    :param float y: latitude coordinate

    :return: col: pixel column number
    :rtype: int
    :return: line: pixel line number
    :rtype: int
    """
    ul_x = geo_transform[0]
    ul_y = geo_transform[3]
    xres = geo_transform[1]
    yres = geo_transform[5]
    col = int(np.round((x - ul_x) / xres))
    line = int(np.round((ul_y - y) / abs(yres)))  # yres has negative size

    return col, line

def _setup_source(input_tif):
    """convenience setup function for gdal_average"""
    src_ds = gdal.Open(input_tif)
    data = src_ds.GetRasterBand(1).ReadAsArray()
    src_dtype = src_ds.GetRasterBand(1).DataType
    mem_driver = gdal.GetDriverByName('MEM')
    src_ds_mem = mem_driver.Create('', src_ds.RasterXSize, src_ds.RasterYSize,2, src_dtype)
    src_ds_mem.GetRasterBand(1).WriteArray(data)
    src_ds_mem.GetRasterBand(1).SetNoDataValue(0)
    # if data==0, then 1, else 0
    nan_matrix = np.isclose(data, 0, atol=1e-6)
    src_ds_mem.GetRasterBand(2).WriteArray(nan_matrix)
    src_ds_mem.SetGeoTransform(src_ds.GetGeoTransform())
    return src_ds, src_ds_mem


def coherence_masking(src_ds, coherence_ds, coherence_thresh):
    """
    Perform coherence masking on raster in-place.

    Based on gdal_calc formula provided by Nahidul:
    gdal_calc.py -A 20151127-20151209_VV_8rlks_flat_eqa.cc.tif
     -B 20151127-20151209_VV_8rlks_eqa.unw.tif
     --outfile=test_v1.tif --calc="B*(A>=0.8)-999*(A<0.8)"
     --NoDataValue=-999

    Args:
        ds: The interferogram to mask as GDAL dataset.
        coherence_ds: The coherence GDAL dataset.
        coherence_thresh: The coherence threshold.
    """
    coherence_band = coherence_ds.GetRasterBand(1)
    src_band = src_ds.GetRasterBand(1)
    # ndv = src_band.GetNoDataValue()
    ndv = np.nan
    coherence = coherence_band.ReadAsArray()
    src = src_band.ReadAsArray()
    var = {'coh': coherence, 'src': src, 't': coherence_thresh, 'ndv': ndv}
    formula = 'where(coh>=t, src, ndv)'
    res = ne.evaluate(formula, local_dict=var)
    src_band.WriteArray(res)
def gdal_average(dst_ds, src_ds, src_ds_mem, thresh):
    """
    Perform subsampling of an image by averaging values

    :param gdal.Dataset dst_ds: Destination gdal dataset object
    :param str input_tif: Input geotif
    :param float thresh: NaN fraction threshold

    :return resampled_average: resampled image data
    :rtype: ndarray
    :return src_ds_mem: Modified in memory src_ds with nan_fraction in Band2. The nan_fraction
        is computed efficiently here in gdal in the same step as the that of
        the resampled average (band 1). This results is huge memory and
        computational efficiency
    :rtype: gdal.Dataset
    """
    src_ds_mem.GetRasterBand(2).SetNoDataValue(-100000)
    src_gt = src_ds.GetGeoTransform()
    src_ds_mem.SetGeoTransform(src_gt)
    gdal.ReprojectImage(src_ds_mem, dst_ds, '', '', gdal.GRA_Average)
    # dst_ds band2 average is our nan_fraction matrix
    nan_frac = dst_ds.GetRasterBand(2).ReadAsArray()
    resampled_average = dst_ds.GetRasterBand(1).ReadAsArray()
    resampled_average[nan_frac >= thresh] = np.nan
    return resampled_average, src_ds_mem


def _alignment(input_tif, new_res, resampled_average, src_ds_mem,
                      src_gt, tmp_ds):
    """
    Correction step to match python multi-look/crop output to match that of
    Legacy data. Modifies the resampled_average array in place.
    """
    src_ds = gdal.Open(input_tif)
    data = src_ds.GetRasterBand(1).ReadAsArray()
    xlooks = ylooks = int(new_res[0] / src_gt[1])
    xres, yres = _get_resampled_data_size(xlooks, ylooks, data)
    nrows, ncols = resampled_average.shape
    # Legacy nearest neighbor resampling for the last
    # [yres:nrows, xres:ncols] cells without nan_conversion
    # turn off nan-conversion
    src_ds_mem.GetRasterBand(1).SetNoDataValue(LOW_FLOAT32)
    # nearest neighbor resapling
    gdal.ReprojectImage(src_ds_mem, tmp_ds, '', '',
                        gdal.GRA_NearestNeighbour)
    # only take the [yres:nrows, xres:ncols] slice
    if nrows > yres or ncols > xres:
        resampled_nearest_neighbor = tmp_ds.GetRasterBand(1).ReadAsArray()
        resampled_average[yres - nrows:, xres - ncols:] = \
            resampled_nearest_neighbor[yres - nrows:, xres - ncols:]

def _get_resampled_data_size(xscale, yscale, data):
    """convenience function mimicking the Legacy output size"""
    xscale = int(xscale)
    yscale = int(yscale)
    ysize, xsize = data.shape
    xres, yres = int(xsize / xscale), int(ysize / yscale)
    return xres, yres

def gdal_dataset(out_fname, columns, rows, driver="GTiff", bands=1, dtype='float32', metadata=None, crs=None, geotransform=None, creation_opts=None):
    """
    Initialises a py-GDAL dataset object for writing image data.
    """
    if dtype == 'float32':
        gdal_dtype = gdal.GDT_Float32
    elif dtype == 'int16':
        gdal_dtype = gdal.GDT_Int16
    else:
        # assume gdal.GDT val is passed to function
        gdal_dtype = dtype

    # create output dataset
    driver = gdal.GetDriverByName(driver)
    outds = driver.Create(out_fname, columns, rows, bands, gdal_dtype, options=creation_opts)

    # geospatial info
    outds.SetGeoTransform(geotransform)
    outds.SetProjection(crs)

    # add metadata
    if metadata is not None:
        for k, v in metadata.items():
            outds.SetMetadataItem(k, str(v))

    return outds



def write_geotiff(data, outds, nodata):
    # pylint: disable=too-many-arguments
    """
    A generic routine for writing a NumPy array to a geotiff.

    :param ndarray data: Output data array to save
    :param obj outds: GDAL destination object
    :param float nodata: No data value of data

    :return None, file saved to disk
    """
    # only support "2 <= dims <= 3"
    if data.ndim == 3:
        count, height, width = data.shape
    elif data.ndim == 2:
        height, width = data.shape
    else:
        msg = "Only support dimensions of '2 <= dims <= 3'."
        raise Exception(msg)

    # write data to geotiff
    band = outds.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    band.WriteArray(data, 0, 0)

    outds = None
    band = None
    del outds
    del band
