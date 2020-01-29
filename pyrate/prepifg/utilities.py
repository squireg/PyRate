import shutil
import os
import numpy as np
from osgeo import gdal

import constants
from constants import ALREADY_SAME_SIZE
from core import config as cf
from core.gdal_python import _crop_resample_setup, _setup_source, gdal_average, _alignment
from core.shared import Ifg, DEM
import numexpr as ne

import logging

gdal.SetCacheMax(2**15)
log = logging.getLogger(__name__)

def prepare_ifg(raster_path, xlooks, ylooks, exts, thresh, crop_opt, write_to_disk=True, out_path=None, header=None, coherence_path=None, coherence_thresh=None):
    """
    Open, resample, crop and optionally save to disk an interferogram or DEM.
    Returns are only given if write_to_disk=False

    :param str raster_path: Input raster file path name
    :param int xlooks: Number of multi-looks in x; 5 is 5 times smaller,
        1 is no change
    :param int ylooks: Number of multi-looks in y
    :param tuple exts: Tuple of user defined georeferenced extents for
        new file: (xfirst, yfirst, xlast, ylast)cropping coordinates
    :param float thresh: see thresh in prepare_ifgs()
    :param int crop_opt: Crop option
    :param bool write_to_disk: Write new data to disk
    :param str out_path: Path for output file
    :param dict header: dictionary of metadata from header file

    :return: resampled_data: output cropped and resampled image
    :rtype: ndarray
    :return: out_ds: destination gdal dataset object
    :rtype: gdal.Dataset
    """
    do_multilook = xlooks > 1 or ylooks > 1
    # resolution=None completes faster for non-multilooked layers in gdalwarp
    resolution = [None, None]
    raster = dem_or_ifg(raster_path)
    log.debug("raster.data_path: " + str(raster.data_path))
    if not raster.is_open:
        raster.open()
    if do_multilook:
        log.debug("Doing do_multilook.")
        resolution = [xlooks * raster.x_step, ylooks * raster.y_step]
    if not do_multilook and crop_opt == ALREADY_SAME_SIZE:

        log.debug("xlooks: " + str(xlooks))
        log.debug("crop_opt: " + str(crop_opt))

        renamed_path = cf.mlooked_path(raster.data_path, looks=xlooks, crop_out=crop_opt)
        log.debug("renamed_path: " + str(renamed_path))

        shutil.copy(raster.data_path, renamed_path)
        # set metadata to indicated has been cropped and multilooked
        # copy file with mlooked path
        return _dummy_warp(renamed_path)

    return _warp(raster, xlooks, ylooks, exts, resolution, thresh, crop_opt, write_to_disk, out_path, header, coherence_path, coherence_thresh)


def _warp(raster, xlooks, ylooks, extent, resolution, thresh, crop_out,
          write_to_disk=True, out_path=None, header=None,
          coherence_path=None, coherence_thresh=None):
    """
    Convenience function for calling GDAL functionality
    """
    if xlooks != ylooks:
        raise ValueError('X and Y looks mismatch')

    # cut, average, resample the final output layers
    op = output_tiff_filename(raster.data_path, out_path)
    looks_path = cf.mlooked_path(op, ylooks, crop_out)

    #     # Add missing/updated metadata to resampled ifg/DEM
    #     new_lyr = type(ifg)(looks_path)
    #     new_lyr.open(readonly=True)
    #     # for non-DEMs, phase bands need extra metadata & conversions
    #     if hasattr(new_lyr, "phase_band"):
    #         # TODO: LOS conversion to vertical/horizontal (projection)
    #         # TODO: push out to workflow
    #         #if params.has_key(REPROJECTION_FLAG):
    #         #    reproject()
    driver_type = 'GTiff' if write_to_disk else 'MEM'
    input_tif = raster.data_path
    extent = extent
    new_res = resolution
    output_file = looks_path
    thresh = thresh
    out_driver_type = driver_type
    hdr = header
    coherence_path = coherence_path
    coherence_thresh = coherence_thresh
    match_pyrate = False

    dst_ds, _, _, _ = _crop_resample_setup(
        extent, input_tif, new_res, output_file,
        out_bands=2, dst_driver_type='MEM')

    # make a temporary copy of the dst_ds for PyRate style prepifg
    tmp_ds = gdal.GetDriverByName('MEM').CreateCopy('', dst_ds) \
        if (match_pyrate and new_res[0]) else None

    src_ds, src_ds_mem = _setup_source(input_tif)

    if coherence_path and coherence_thresh:
        coherence_raster = dem_or_ifg(coherence_path)
        coherence_raster.open()
        coherence_ds = coherence_raster.dataset
        coherence_masking(src_ds_mem, coherence_ds, coherence_thresh)
    elif coherence_path and not coherence_thresh:
        raise ValueError(f"Coherence file provided without a coherence "
                         f"threshold. Please ensure you provide 'cohthresh' "
                         f"in your config if coherence masking is enabled.")

    resampled_average, src_ds_mem = \
        gdal_average(dst_ds, src_ds, src_ds_mem, thresh)
    src_dtype = src_ds_mem.GetRasterBand(1).DataType
    src_gt = src_ds_mem.GetGeoTransform()

    # required to match Legacy output
    if tmp_ds:
        _alignment(input_tif, new_res, resampled_average, src_ds_mem,
                          src_gt, tmp_ds)

    # grab metadata from existing geotiff
    gt = dst_ds.GetGeoTransform()
    wkt = dst_ds.GetProjection()

    # TEST HERE IF EXISTING FILE HAS PYRATE METADATA. IF NOT ADD HERE
    if not constants.DATA_TYPE in dst_ds.GetMetadata() and hdr is not None:
        md = collate_metadata(hdr)
    else:
        md = dst_ds.GetMetadata()

    # update metadata for output
    for k, v in md.items():
        if k == constants.DATA_TYPE:
            # update data type metadata
            if v == constants.ORIG and coherence_path:
                md.update({constants.DATA_TYPE: constants.COHERENCE})
            elif v == constants.ORIG and not coherence_path:
                md.update({constants.DATA_TYPE: constants.MULTILOOKED})
            elif v == constants.DEM:
                md.update({constants.DATA_TYPE: constants.MLOOKED_DEM})
            elif v == constants.INCIDENCE:
                md.update({constants.DATA_TYPE: constants.MLOOKED_INC})
            elif v == constants.COHERENCE and coherence_path:
                pass
            elif v == constants.MULTILOOKED and coherence_path:
                md.update({constants.DATA_TYPE: constants.COHERENCE})
            elif v == constants.MULTILOOKED and not coherence_path:
                pass
            else:
                raise TypeError('Data Type metadata not recognised')

    # In-memory GDAL driver doesn't support compression so turn it off.
    creation_opts = ['compress=packbits'] if out_driver_type != 'MEM' else []
    out_ds = gdal_dataset(output_file, dst_ds.RasterXSize, dst_ds.RasterYSize,
                                 driver=out_driver_type, bands=1, dtype=src_dtype, metadata=md, crs=wkt,
                                 geotransform=gt, creation_opts=creation_opts)

    write_geotiff(resampled_average, out_ds, np.nan)
    log.debug("Writing geotiff: "+str(out_ds))
    # return resampled_average, out_ds
    if not write_to_disk:
        return resampled_average, out_ds


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

def output_tiff_filename(inpath, outpath):
    """
    Output geotiff filename for a given input filename.

    :param str inpath: path of input file location
    :param str outpath: path of output file location

    :return: Geotiff filename for the given file.
    :rtype: str
    """
    fname, ext = os.path.basename(inpath).split('.')
    outpath = os.path.dirname(inpath) if outpath is None else outpath
    if ext == 'tif':
        name = os.path.join(outpath, fname + '.tif')
    else:
        name = os.path.join(outpath, fname + '_' + ext + '.tif')
    return name


def dem_or_ifg(data_path):
    """
    Returns an Ifg or DEM class object from input geotiff file.

    :param str data_path: file path name

    :return: Interferogram or DEM object from input file
    :rtype: Ifg or DEM class object
    """
    ds = gdal.Open(data_path)
    md = ds.GetMetadata()
    if constants.MASTER_DATE in md:  # ifg
        return Ifg(data_path)
    else:
        return DEM(data_path)

def _dummy_warp(renamed_path):
    """
    Convenience dummy operation for when no multi-looking or cropping
    required
    """
    ifg = dem_or_ifg(renamed_path)
    ifg.open()
    ifg.dataset.SetMetadataItem(constants.DATA_TYPE, constants.MULTILOOKED)
    data = ifg.dataset.ReadAsArray()
    return data, ifg.dataset


def collate_metadata(header):
    """
    Grab metadata relevant to PyRate from input metadata

    :param dict header: Input file metadata dictionary

    :return: dict of relevant metadata for PyRate
    """
    md = dict()
    if _is_interferogram(header):
        for k in [constants.PYRATE_WAVELENGTH_METRES, constants.PYRATE_TIME_SPAN, constants.PYRATE_INSAR_PROCESSOR,
                  constants.MASTER_DATE, constants.SLAVE_DATE, constants.DATA_UNITS, constants.DATA_TYPE]:
            md.update({k: str(header[k])})
        if header[constants.PYRATE_INSAR_PROCESSOR] == constants.GAMMA:
            for k in [constants.MASTER_TIME, constants.SLAVE_TIME, constants.PYRATE_INCIDENCE_DEGREES]:
                md.update({k: str(header[k])})
    elif _is_incidence(header):
        md.update({constants.DATA_TYPE: constants.INCIDENCE})
    else: # must be dem
        md.update({constants.DATA_TYPE: constants.DEM})

    return md

def _is_interferogram(hdr):
    """
    Convenience function to determine if file is interferogram
    """
    return constants.PYRATE_WAVELENGTH_METRES in hdr


def _is_incidence(hdr):
    """
    Convenience function to determine if incidence file
    """
    return 'FILE_TYPE' in hdr


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
