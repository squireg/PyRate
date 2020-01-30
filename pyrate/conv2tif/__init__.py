from osgeo import osr, gdal
from constants import GDAL_CACHE_MAX, NO_OF_PARALLEL_PROCESSES
import os
import time
import multiprocessing
import logging
from conv2tif import geotiff
from conv2tif import gamma
from conv2tif import roipac
from constants import NO_OF_PARALLEL_PROCESSES

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def main(config):
    start_time = time.time()
    gdal.SetCacheMax(GDAL_CACHE_MAX)

    # check if all the geotiff exist
    list_of_possible_output_file = []

    list_of_possible_output_file.extend([interferogram_file.converted_path for interferogram_file in config.interferogram_files])
    list_of_possible_output_file.append(config.dem_file.converted_path)
    if config.coherence_file_paths is not None:
        list_of_possible_output_file.extend([interferogram_file.converted_path for interferogram_file in config.coherence_file_paths])

    all_output_geotiff_exists = all(os.path.isfile(output_file) for output_file in list_of_possible_output_file)
    if all_output_geotiff_exists:
        log.info("Updating GeoTIFF header information.")

        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(NO_OF_PARALLEL_PROCESSES)

        # Running pools
        pool.map(geotiff.update_header, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

    elif config.processor:
        log.info("Gamma processor selected.")

        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(NO_OF_PARALLEL_PROCESSES)

        # Running pools to convert gamma file to GeoTIFF
        pool.map(gamma.convert_gamma_interferogram, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

        # Convert coherence files
        if config.coherence_file_paths is not None:
            for coherence_file in config.coherence_file_paths:
                gamma.convert_gamma_interferogram(config, coherence_file)

        # Convert dem file to GeoTIFF
        gamma.convert_dem_interferogram(config)

        # Convert coherence file to GeoTIFF

    else:
        log.info("ROIPAC processor selected.")
        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(NO_OF_PARALLEL_PROCESSES)

        # Running pools
        pool.map(roipac.convert_roipac_interferogram, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

        # Convert dem file to GeoTIFF
        roipac.convert_dem_interferogram(config)

        # Convert coherence file to GeoTIFF

    log.info("--- %s seconds ---" % (time.time() - start_time))
