from osgeo import osr, gdal
from constants import GDAL_CACHE_MAX
import os
import time
import multiprocessing
import logging
from conv2tif import geotiff
from conv2tif import gamma
from conv2tif import roipac

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def main(config):
    start_time = time.time()
    gdal.SetCacheMax(GDAL_CACHE_MAX)

    # check if all the geotiff exist
    all_geotiff_exists = all(os.path.isfile(interferogram_file.converted_path) for interferogram_file in config.interferogram_files)
    if all_geotiff_exists:
        log.info("Updating GeoTIFF header information.")

        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(multiprocessing.cpu_count())

        # Running pools
        pool.map(geotiff.update_header, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

    elif config.processor:
        log.info("Gamma processor selected.")

        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(multiprocessing.cpu_count())

        # Running pools to convert gamma file to GeoTIFF
        pool.map(gamma.convert_gamma_interferogram, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

        # Convert dem file to GeoTIFF
        gamma.convert_dem_interferogram(config)

        # Convert coherence file to GeoTIFF

    else:
        log.info("ROIPAC processor selected.")
        # Init multiprocessing.Pool()
        pool = multiprocessing.Pool(multiprocessing.cpu_count())

        # Running pools
        pool.map(roipac.convert_roipac_interferogram, [(config, interferogram_file) for interferogram_file in config.interferogram_files])

        # Closing pools
        pool.close()

        # Convert dem file to GeoTIFF
        roipac.convert_dem_interferogram(config)

        # Convert coherence file to GeoTIFF

    log.info("--- %s seconds ---" % (time.time() - start_time))
