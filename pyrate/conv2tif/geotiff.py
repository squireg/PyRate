from osgeo import osr, gdal
import numpy as np
import struct
from datetime import datetime, timedelta
import statistics
from conv2tif.utilities import *
from constants import *
import pathlib
import logging
import multiprocessing

# make numpy thread safe
os.environ['NUMEXPR_MAX_THREADS'] = str(NO_OF_PARALLEL_PROCESSES)
# do not create aux.xml file
os.environ['GDAL_PAM_ENABLED'] = 'NO'
# feature root logger for PyRate
log = logging.getLogger(__name__)


def update_header(parameters):
    config, interferogram_file = parameters
    if config.processor:
        update_gamma_header(parameters)
    else:
        update_roipac_header(parameters)


def update_gamma_header(parameters):

    config, interferogram_file = parameters
    # define total processes running in parallel
    os.environ['NUMEXPR_MAX_THREADS'] = config.NUMEXPR_MAX_THREADS
    log.info("Start processing interferogram: " + interferogram_file.unwrapped_path)
    # for the given interferogram find the master and slave header files
    header_master_path, header_slave_path = sort_headers(config.header_file_paths, interferogram_file.unwrapped_path)

    # read headers
    master_header = read_raw_header_file(header_master_path)
    slave_header = read_raw_header_file(header_slave_path)

    output_dataset = gdal.Open(interferogram_file.converted_path, gdal.GA_Update)

    # create metadata
    master_frequency = format_header_value(master_header["root"]["radar_frequency"], r'[\+\-]?\d+[.]\d+[e][\+\-]\d+', float, 0.00001)
    slave_frequency = format_header_value(master_header["root"]["radar_frequency"], r'[\+\-]?\d+[.]\d+[e][\+\-]\d+', float, 0.00001)

    mean_frequency = statistics.mean([master_frequency, slave_frequency])
    round_spaces = len(str(mean_frequency).split(".")[1]) - 1
    mean_frequency = round(mean_frequency, round_spaces)

    wavelength_metres = SPEED_OF_LIGHT_METRES_PER_SECOND / mean_frequency

    master_date = datetime.strptime(" ".join(master_header["root"]["date"].split(" ")[:3]), "%Y %d %M")
    slave_date = datetime.strptime(" ".join(slave_header["root"]["date"].split(" ")[:3]), "%Y %d %M")
    time_span_year = (master_date.day - slave_date.day) / DAYS_PER_YEAR

    if "center_time" in list(master_header["root"]):
        master_time = str(timedelta(seconds=float(re.match(r'\d+[\.]?\d+', master_header["root"]["center_time"])[0])).split('.')[0])
        slave_time = str(timedelta(seconds=float(re.match(r'\d+[\.]?\d+', slave_header["root"]["center_time"])[0])).split('.')[0])
    else:
        master_time = master_header["root"]["date"].split(" ")[3:]
        master_time = str(timedelta(hours=float(master_time[0]), minutes=float(master_time[1]), seconds=float(master_time[2])))

        slave_time = slave_header["root"]["date"].split(" ")[3:]
        slave_time = str(timedelta(hours=float(slave_time[0]), minutes=float(slave_time[1]),seconds=float(slave_time[2])))

    incidence_angle_master = float(re.match(r'\d+[.]?\d+', master_header["root"]["incidence_angle"])[0])
    incidence_angle_slave = float(re.match(r'\d+[.]?\d+', slave_header["root"]["incidence_angle"])[0])
    incidence_angle_mean = statistics.mean([incidence_angle_master, incidence_angle_slave])
    round_spaces = len(str(incidence_angle_mean).split(".")[1]) - 1
    incidence_angle_mean = round(incidence_angle_mean, round_spaces)

    metadata = output_dataset.GetMetadata()
    metadata.update({
        'WAVELENGTH_METRES': str(wavelength_metres),
        'TIME_SPAN_YEAR': str(time_span_year),
        'INSAR_PROCESSOR': 'GAMMA',
        'MASTER_DATE': master_date.strftime("%Y-%d-%M"),
        'SLAVE_DATE': slave_date.strftime("%Y-%d-%M"),
        'DATA_UNITS': 'RADIANS',
        'DATA_TYPE': 'ORIGINAL_IFG',
        'MASTER_TIME': master_time,
        'SLAVE_TIME': slave_time,
        'INCIDENCE_DEGREES': str(incidence_angle_mean)
    })
    output_dataset.SetMetadata(metadata)
    # manual close dataset
    output_dataset = None
    del output_dataset

    log.info("Finish processing interferogram: " + interferogram_file.converted_path)

def update_roipac_header(parameters):
    None