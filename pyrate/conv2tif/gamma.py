from osgeo import osr, gdal
import numpy as np
import struct
from datetime import datetime, timedelta
import statistics
from conv2tif.utilities import *
from constants import *
import pathlib
import logging

os.environ['NUMEXPR_MAX_THREADS'] = str(NO_OF_PARALLEL_PROCESSES)
log = logging.getLogger(__name__)


def convert_dem_interferogram(config):

    log.info("Start processing: " + str(config.dem_file.unwrapped_path))


    # read dem headers
    dem_header = read_raw_header_file(config.demHeaderFile)

    # get extent for the dataset
    x_size = format_header_value(dem_header["root"]["width"], r'[\+\-]?\d+', int)
    y_size = format_header_value(dem_header["root"]["nlines"], r'[\+\-]?\d+', int)

    longitude = format_header_value(dem_header["root"]["corner_lon"], r'[\+\-]?\d+[.]\d+', float)
    x_step = format_header_value(dem_header["root"]["post_lon"], r'[\+\-]?\d+[.]\d+[e][\+\-]\d+', float)

    latitude = format_header_value(dem_header["root"]["corner_lat"], r'[\+\-]?\d+[.]\d+', float)
    y_step = format_header_value(dem_header["root"]["post_lat"], r'[\+\-]?\d+[.]\d+[e][\-]\d+', float)

    # create an empty dataset
    driver = gdal.GetDriverByName("GTiff")
    output_dataset = driver.Create(str(config.dem_file.converted_path), x_size, y_size, DATA_BANDS, gdal.GDT_Int16, options=['compress=packbits'])

    # add geo-spatial info
    geo_transform = [longitude, x_step, 0, latitude, 0, y_step]
    output_dataset.SetGeoTransform(geo_transform)
    srs = osr.SpatialReference()
    wkt_projection = srs.ExportToWkt()
    output_dataset.SetProjection(wkt_projection)
    band = output_dataset.GetRasterBand(1)
    band.SetNoDataValue(NO_DATA_VALUE)

    # set metadata
    meta_data = output_dataset.GetMetadata()
    meta_data.update({
        'AREA_OR_POINT': 'Area',
        'DATA_TYPE': 'ORIGINAL_DEM'
    })
    output_dataset.SetMetadata(meta_data)

    # create output dataset
    fmtstr = '!' + ('f' * x_size)
    bytes_per_col = 4
    row_bytes = x_size * bytes_per_col

    with open(config.dem_file.unwrapped_path, 'rb') as f:
        # Read the input array byte by byte and write it to the new dataset
        for y in range(y_size):
            data = struct.unpack(fmtstr, f.read(row_bytes))
            # write data to geo-tiff
            band.WriteArray(np.array(data).reshape(1, x_size), yoff=y)

    band.FlushCache()  # Write to disk
    output_dataset = None  # manual close dataset
    del output_dataset
    log.info("Finish processing interferogram: " + str(config.dem_file.converted_path))


def convert_gamma_interferogram(parameters):

    config, interferogram_file = parameters
    # define total processes running in parallel
    os.environ['NUMEXPR_MAX_THREADS'] = config.NUMEXPR_MAX_THREADS
    log.info("Start processing interferogram: " + interferogram_file.unwrapped_path)
    # for the given interferogram find the master and slave header files
    header_master_path, header_slave_path = sort_headers(config.header_file_paths, interferogram_file.unwrapped_path)

    # read headers
    master_header = read_raw_header_file(header_master_path)
    slave_header = read_raw_header_file(header_slave_path)

    # read dem headers
    dem_header = read_raw_header_file(config.demHeaderFile)

    # get extent for the dataset
    x_size = format_header_value(dem_header["root"]["width"], r'[\+\-]?\d+', int)
    y_size = format_header_value(dem_header["root"]["nlines"], r'[\+\-]?\d+', int)

    longitude = format_header_value(dem_header["root"]["corner_lon"], r'[\+\-]?\d+[.]\d+', float)
    x_step = format_header_value(dem_header["root"]["post_lon"], r'[\+\-]?\d+[.]\d+[e][\+\-]\d+', float)

    latitude = format_header_value(dem_header["root"]["corner_lat"], r'[\+\-]?\d+[.]\d+', float)
    y_step = format_header_value(dem_header["root"]["post_lat"], r'[\+\-]?\d+[.]\d+[e][\-]\d+', float)

    # create an empty dataset
    driver = gdal.GetDriverByName("GTiff")
    output_dataset = driver.Create(interferogram_file.converted_path, x_size, y_size, DATA_BANDS, gdal.GDT_Float32, options=['compress=packbits'])

    # add geo-spatial info
    geo_transform = [longitude, x_step, 0, latitude, 0, y_step]
    output_dataset.SetGeoTransform(geo_transform)
    srs = osr.SpatialReference()
    wkt_projection = srs.ExportToWkt()
    output_dataset.SetProjection(wkt_projection)
    band = output_dataset.GetRasterBand(1)
    band.SetNoDataValue(NO_DATA_VALUE)

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


    metadata = {
        'WAVELENGTH_METRES': wavelength_metres,
        'TIME_SPAN_YEAR': time_span_year,
        'INSAR_PROCESSOR': 'GAMMA',
        'MASTER_DATE': master_date.strftime("%Y-%d-%M"),
        'SLAVE_DATE': slave_date.strftime("%Y-%d-%M"),
        'DATA_UNITS': 'RADIANS',
        'DATA_TYPE': 'ORIGINAL_IFG',
        'MASTER_TIME': master_time,
        'SLAVE_TIME': slave_time,
        'INCIDENCE_DEGREES': incidence_angle_mean,
        'AREA_OR_POINT': "Area"
    }

    if metadata is not None:
        for k, v in metadata.items():
            output_dataset.SetMetadataItem(k, str(v))

    # create output dataset
    fmtstr = '!' + ('f' * x_size)
    bytes_per_col = 4
    row_bytes = x_size * bytes_per_col

    with open(interferogram_file.unwrapped_path, 'rb') as f:
        # Read the input array byte by byte and write it to the new dataset
        for y in range(y_size):

            data = struct.unpack(fmtstr, f.read(row_bytes))
            # write data to geo-tiff
            band.WriteArray(np.array(data).reshape(1, x_size), yoff=y)

    # manual close dataset
    band.FlushCache()  # Write to disk
    output_dataset = None
    del output_dataset
    log.info("Finish processing interferogram: " + interferogram_file.converted_path)

