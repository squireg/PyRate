"""
Prepares input files and associated data for the PyRate work flow. 

Input rasters often may cropping, scaling, and multilooking/downsampling to
coarser grids before being processed. This module uses gdalwarp to handle these
operations.

The rasters need to be in GeoTIFF format with PyRate specific metadata headers.  

Created on 23/10/2012
@author: Ben Davies, NCI
"""

# TODO: check new average option for gdalwarp (GDAL 1.10.x +) 
# TODO: Wavelength conversion 

import os, sys
from math import modf
from numbers import Number
from tempfile import mkstemp
from itertools import product
from subprocess import check_call
from os.path import join, splitext

from numpy import array, where, nan, isnan, nanmean, float32, zeros, sum as nsum

from shared import Ifg, DEM
from config import parse_namelist
from config import OBS_DIR, IFG_CROP_OPT, IFG_LKSX, IFG_LKSY, IFG_FILE_LIST
from config import IFG_XFIRST, IFG_XLAST, IFG_YFIRST, IFG_YLAST, DEM_FILE


# Constants
MINIMUM_CROP = 1
MAXIMUM_CROP = 2
CUSTOM_CROP = 3
ALREADY_SAME_SIZE = 4
CROP_OPTIONS = [MINIMUM_CROP, MAXIMUM_CROP, CUSTOM_CROP, ALREADY_SAME_SIZE]

GRID_TOL = 1e-6


# FIXME: push files out to params OUT dir
# TODO: expand args instead of using params? (more args, but less dependencies)
def prepare_ifgs(params, thresh=0.5, verbose=False):
	"""
	Produces multilooked/resampled data files for PyRate analysis.
	params: dict of named values (from pyrate config file)
	thresh: 0.0->1.0 controls NaN handling when resampling to coarser grids.
	    Value is the proportion above which the number of NaNs in an area is
	    considered invalid. thresh=0 resamples to NaN if 1 or more contributing
	    cells are NaNs. At 0.25, it resamples to NaN if 1/4 or more contributing
	    cells are NaNs. At 1.0, areas are resampled to NaN only if all
	    contributing cells are NaNs.
	verbose - controls level of gdalwarp output
	"""
	# validate config file settings
	crop_opt = params[IFG_CROP_OPT]
	if crop_opt not in CROP_OPTIONS:
		msg = "Unrecognised crop option: %s" % params[IFG_CROP_OPT]
		raise PreprocessError(msg)

	check_looks(params)
	srcdir = params[OBS_DIR]
	paths = [join(srcdir, p) for p in parse_namelist(params[IFG_FILE_LIST])]
	ifgs = [Ifg(p) for p in paths]

	# treat DEM as an Ifg as API is mostly shared
	if DEM_FILE in params:
		ifgs.append(DEM(params[DEM_FILE]))

	for i in ifgs:
		i.open()

	check_resolution(ifgs)

	# Determine cmd line args for gdalwarp calls for each ifg (gdalwarp has no
	# API. For resampling, gdalwarp is called 2x. 1st to subset the source data
	# for Pirate style averaging/resampling, 2nd to generate the final dataset
	# with correct extents/shape/cell count. Without resampling, gdalwarp is
	# only needed to cut out the required segment.
	xlooks, ylooks = params[IFG_LKSX], params[IFG_LKSY]
	resolution = [xlooks * i.x_step, ylooks * i.y_step]

	extents = get_extents(ifgs, params)
	multi = []

	for i in ifgs:
		# TODO: comment on resolution calc/optimisation
		res = None if resolution == [i.x_step, i.y_step] else resolution
		ifgx = warp(i, xlooks, ylooks, extents, res, thresh, verbose)
		multi.append(ifgx)

	return multi

# TODO: refactor with extents tuple
def get_extents(ifgs, params):
	'Returns extents/bounding box args for gdalwarp as strings'
	crop_opt = params[IFG_CROP_OPT]
	if crop_opt == MINIMUM_CROP:
		xmin, ymin, xmax, ymax = min_bounds(ifgs)
	elif crop_opt == MAXIMUM_CROP:
		xmin, ymin, xmax, ymax = max_bounds(ifgs)
	elif crop_opt == CUSTOM_CROP:
		xmin, xmax = params[IFG_XFIRST], params[IFG_XLAST]
		ymin, ymax = params[IFG_YLAST], params[IFG_YFIRST]
	else:
		xmin, ymin, xmax, ymax = get_same_bounds(ifgs)

	# FIXME: add and test this? (or consider GDALwarp breakage enough?)
	#assert xmin < xmax
	#assert ymin < ymax

	check_crop_coords(ifgs, xmin, xmax, ymin, ymax)
	return [str(s) for s in (xmin, ymin, xmax, ymax)]


def _file_ext(raster):
	'''Returns file ext string based on type of raster.'''
	if isinstance(raster, Ifg):
		return "tif"
	elif isinstance(raster, DEM):
		return "dem"
	else:
		# TODO: several possible file types to implement:
		# LOS file:  has 2 bands: beam incidence angle & ground azimuth)
		# Baseline file: perpendicular baselines (single band?)
		raise NotImplementedError("Missing raster types for LOS and baseline")


def _resample_ifg(ifg, cmd, x_looks, y_looks, thresh):
	'''Convenience function to resample data from a given Ifg (more coarse).'''

	# HACK: create tmp ifg, extract data array for manual resampling as gdalwarp
	# lacks Pirate's averaging method
	tmp_path = mkstemp()[1]
	check_call(cmd + [ifg.data_path, tmp_path])
	tmp = type(ifg)(tmp_path) # dynamically handle Ifgs & Rasters
	tmp.open()

	if isinstance(ifg, Ifg):
		# TODO: add an option to retain amplitude band (resample this if reqd)
		data = tmp.phase_band.ReadAsArray()
		data = where(data == 0, nan, data) # flag incoherent cells as NaNs
	elif isinstance(ifg, DEM):
		data = tmp.height_band.ReadAsArray()
	else:
		# TODO: need to handle resampling of LOS and baseline files
		raise NotImplementedError("Resampling for LOS & baseline not implemented.")

	del tmp # manual close
	os.remove(tmp_path)
	return resample(data, x_looks, y_looks, thresh)


def warp(ifg, x_looks, y_looks, extents, resolution, thresh, verbose):
	'''
	Resamples 'ifg' and returns a new Ifg obj.
	xlooks: integer factor to scale X axis by, 5 is 5x smaller, 1 is no change.
	ylooks: as xlooks, but for Y axis
	extents: georeferenced extents for new file: (xmin, ymin, xmax, ymax)
	resolution: [xres, yres] or None. Sets resolution output Ifg metadata. Use
	            None if raster size is not being changed.
	thresh: see thresh in prepare_ifgs().
	verbose: True to print gdalwarp output to stdout
	'''
	# dynamically build command for call to gdalwarp
	cmd = ["gdalwarp", "-overwrite", "-srcnodata", "None", "-te"] + extents
	if not verbose: cmd.append("-q")

	# HACK: if resampling, cut segment with gdalwarp & manually average tiles
	data = None
	if resolution:
		data = _resample_ifg(ifg, cmd, x_looks, y_looks, thresh)
		cmd += ["-tr"] + [str(r) for r in resolution] # change res of final output

	# use GDAL to cut (and resample) the final output layers
	s = splitext(ifg.data_path)
	ext = _file_ext(ifg)
	looks_path = s[0] + "_%srlks.%s" % (y_looks, ext)
	cmd += [ifg.data_path, looks_path]
	check_call(cmd)

	# Add missing/updated metadata to resampled ifg/DEM
	new_lyr = type(ifg)(looks_path)
	new_lyr.open(readonly=False)
	#_create_new_roipac_header(ifg, new_lyr)

	# for non-DEMs, phase bands need extra metadata & conversions
	if hasattr(new_lyr, "phase_band"):
		new_lyr.phase_band.SetNoDataValue(nan)

		if data is None: # data wasn't resampled, so flag incoherent cells
			data = new_lyr.phase_band.ReadAsArray()
			data = where(data == 0, nan, data)

		# TODO: LOS conversion to vertical/horizontal (projection)
		#if params.has_key(PROJECTION_FLAG):
		#	reproject()

		# tricky: write either resampled or the basic cropped data to new layer
		new_lyr.phase_band.WriteArray(data)
		new_lyr.nan_converted = True

	return new_lyr


def resample(data, xscale, yscale, thresh):
	"""
	Resamples/averages 'data' to return an array from the averaging of blocks
	of several tiles in 'data'. NB: Assumes incoherent cells are NaNs.

	data: source array to resample to different size
	xscale: number of cells to average along X axis
	yscale: number of Y axis cells to average
	thresh: minimum allowable proportion of NaN cells (range from 0.0-1.0),
	eg. 0.25 = 1/4 or more as NaNs results in a NaN value for the output cell.
	"""
	if thresh < 0 or thresh > 1:
		raise ValueError("threshold must be >= 0 and <= 1")

	xscale = int(xscale)
	yscale = int(yscale)

	ysize, xsize = data.shape
	xres, yres = (xsize / xscale), (ysize / yscale)
	dest = zeros((yres, xres), dtype=float32) * nan
	tile_cell_count = xscale * yscale

	# calc mean without nans (fractional threshold ignores tiles with excess NaNs)
	for y,x in product(xrange(yres), xrange(xres)):
		tile = data[y * yscale : (y+1) * yscale, x * xscale : (x+1) * xscale]
		nan_fraction = nsum(isnan(tile)) / float(tile_cell_count)

		if nan_fraction < thresh or (nan_fraction == 0 and thresh == 0):
			dest[y,x] = nanmean(tile)

	return dest


def reproject():
	raise NotImplementedError("TODO: Reprojection LOS/Horiz/Vert")


def check_resolution(ifgs):
	"""Verifies Ifg resolutions are equal for the given grids"""
	for var in ['x_step', 'y_step']:
		values = array([getattr(i, var) for i in ifgs])
		if not (values == values[0]).all():
			msg = "Grid resolution does not match for %s" % var
			raise PreprocessError(msg)


def check_looks(params):
	"""Verifies looks parameters are valid"""
	xscale = params[IFG_LKSX]
	yscale = params[IFG_LKSY]
	if not (isinstance(xscale, Number) and isinstance(yscale, Number)):
		msg = "Non-numeric looks parameter(s), x: %s, y: %s" % (xscale, yscale)
		raise PreprocessError(msg)

	if not (xscale > 0 and yscale > 0):
		msg = "Invalid looks parameter(s), x: %s, y: %s" % (xscale, yscale)
		raise PreprocessError(msg)


def min_bounds(ifgs):
	'''Returns bounds for overlapping area of the given interferograms.'''
	xmin = max([i.x_first for i in ifgs])
	ymax = min([i.y_first for i in ifgs])
	xmax = min([i.x_last for i in ifgs])
	ymin = max([i.y_last for i in ifgs])
	return xmin, ymin, xmax, ymax


def max_bounds(ifgs):
	'''Returns bounds for the total area covered by the given interferograms.'''
	xmin = min([i.x_first for i in ifgs])
	ymax = max([i.y_first for i in ifgs])
	xmax = max([i.x_last for i in ifgs])
	ymin = min([i.y_last for i in ifgs])
	return xmin, ymin, xmax, ymax

def get_same_bounds(ifgs):
	'Check and return bounding box for ALREADY_SAME_SIZE option'
	tfs = [i.dataset.GetGeoTransform() for i in ifgs]
	equal = [t == tfs[0] for t in tfs[1:]]
	if not all(equal):
		msg = 'Ifgs do not have the same bounding box for crop option: %s'
		raise PreprocessError(msg % ALREADY_SAME_SIZE)

	xmin, xmax = i.x_first, i.x_last
	ymin, ymax = i.y_first, i.y_last

	# swap y_first & y_last when using southern hemisphere -ve coords
	if ymin > ymax:
		ymin, ymax = ymax, ymin

	return xmin, ymin, xmax, ymax


def check_crop_coords(ifgs, xmin, xmax, ymin, ymax):
	'''Ensures cropping coords line up with grid system within tolerance.'''
	# NB: assumption is the first Ifg is correct, so only test against it
	i = ifgs[0]
	for par, crop, step in zip(['x_first', 'x_last', 'y_first', 'y_last'],
								[xmin, xmax, ymax, ymin],
								[i.x_step, i.x_step, i.y_step, i.y_step]):

		# is diff of the given extent from grid a multiple of X|Y_STEP ?
		param = getattr(i, par)
		diff = abs(crop - param)
		remainder = abs(modf(diff / step)[0])

		# handle cases where division gives remainder near zero, or just < 1
		if remainder > GRID_TOL and remainder < (1 - GRID_TOL):
			msg = "%s crop extent not within %s of grid coordinate"
			raise PreprocessError(msg % (par, GRID_TOL))


class PreprocessError(Exception):
	pass
