'''
Collection of generic testing utils and mock objs for PyRate
Author: Ben Davies
'''

import os
import glob
from os.path import join

from pyrate.shared import Ifg
from numpy import isnan, sum as nsum

BASE_TEST = join(os.environ['PYRATEPATH'], "tests")
SYD_TEST_DIR = join(BASE_TEST, "sydney_test")
SYD_TEST_OBS = join(SYD_TEST_DIR, 'obs')

SYD_TEST_DEM = join(SYD_TEST_DIR, 'dem/sydney_trimmed.dem')
SYD_TEST_DEM_HDR = join(SYD_TEST_DIR, 'dem/sydney_trimmed.dem.rsc')
SYD_TEST_DEM_DIR = join(SYD_TEST_DIR, 'dem')

PREP_TEST_DIR = join(BASE_TEST, 'prepifg')
PREP_TEST_OBS = join(PREP_TEST_DIR, 'obs')

SINGLE_TEST_DIR = join(BASE_TEST, 'single')
HEADERS_TEST_DIR = join(BASE_TEST, 'headers')
INCID_TEST_DIR = join(BASE_TEST, 'incidence')

GAMMA_TEST_DIR = join(BASE_TEST, "gamma")



# small dummy ifg list to limit overall # of ifgs
IFMS5 = """geo_060828-061211.unw
geo_061106-061211.unw
geo_061106-070115.unw
geo_061106-070326.unw
geo_070326-070917.unw
"""

# TODO: get rid of first returned arg?
def sydney_data_setup():
	'''Returns Ifg objs for the files in the sydney test dir'''
	datafiles = glob.glob(join(SYD_TEST_OBS, "*.unw") )
	ifgs = [Ifg(i) for i in datafiles]
	for i in ifgs:
		i.open()

	return ifgs


def sydney5_ifgs():
	'''Convenience func to return a subset of 5 linked Ifgs from the testdata'''
	return [Ifg(join(SYD_TEST_OBS, p)) for p in IFMS5.split()]


def sydney5_mock_ifgs(xs=3, ys=4):
	'''Returns smaller mocked version of sydney Ifgs for testing'''
	ifgs = sydney5_ifgs()
	for i in ifgs: i.open()
	mocks = [MockIfg(i, xs, ys) for i in ifgs]
	for i,m in zip(ifgs, mocks):
		m.phase_data = i.phase_data[:ys,:xs]

	return mocks



class MockIfg(object):
	'''Mock Ifg for detailed testing'''

	def __init__(self, ifg, xsize=None, ysize=None):
		'''
		Creates mock Ifg based on a given interferogram. Size args specify the
		dimensions of the phase band (so the mock ifg can be resized differently
		to the source interferogram for smaller test datasets).
		'''
		self.MASTER = ifg.MASTER
		self.SLAVE = ifg.SLAVE
		self.DATE12 = ifg.DATE12

		self.FILE_LENGTH = ysize
		self.WIDTH = xsize
		self.X_SIZE = ifg.X_SIZE
		self.Y_SIZE = ifg.Y_SIZE
		self.X_STEP = ifg.X_STEP
		self.Y_STEP = ifg.Y_STEP
		self.num_cells = ysize * xsize
		self.phase_data = ifg.phase_data[:ysize, :xsize]
		self.nan_fraction = ifg.nan_fraction # use existing overall nan fraction

	def open(self):
		pass # can't open anything!

	@property
	def nan_count(self):
		return nsum(isnan(self.phase_data))

	@property
	def shape(self):
		return (self.FILE_LENGTH, self.WIDTH)