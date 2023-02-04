#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""

"""

import os
import sys
import h5py as h5
import numpy
import numpy.typing
import argparse
from typing import Any, List, Dict, Union, Tuple, TextIO, cast
from utils import crystfel_geometry
from numpy.typing import NDArray
import fabio
from pathlib import Path
import glob
import re

os.nice(0)


class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('-d', '--d', type=str, help="Directory of interest")
    parser.add_argument('-r', '--r', type=str, help="Directory with raw files")
    parser.add_argument('-h5p', '--h5p', type=str, help="hdf5 path for the cxi input_file data")
    parser.add_argument('-o', '--o',type=str, help="Output path")
    parser.add_argument('-g', '--g',type=str, help="Geometry input_file")
    return parser.parse_args()


def load_geometry(geometry_lines: List[str]) -> None:
    # Loads CrystFEL goemetry using om.utils module.
    parameter_geometry: crystfel_geometry.TypeDetector
    beam: crystfel_geometry.TypeBeam
    parameter_geometry, beam, __ = crystfel_geometry.read_crystfel_geometry(
        text_lines=geometry_lines
    )
    parameter_pixelmaps: crystfel_geometry.TypePixelMaps = (
        crystfel_geometry.compute_pix_maps(geometry=parameter_geometry)
    )

    first_panel: str = list(parameter_geometry["panels"].keys())[0]
    parameter_pixel_size: float = parameter_geometry["panels"][first_panel]["res"]
    parameter_clen_from: str = parameter_geometry["panels"][first_panel]["clen_from"]
    if parameter_clen_from == "":
        parameter_clen: float = parameter_geometry["panels"][first_panel]["clen"]
    parameter_coffset: float = parameter_geometry["panels"][first_panel]["coffset"]
    parameter_photon_energy_from: str = beam["photon_energy_from"]
    if parameter_photon_energy_from == "":
        parameter_photon_energy: float = beam["photon_energy"]
    parameter_mask_filename = parameter_geometry["panels"][first_panel]["mask_file"]
    parameter_mask_hdf5_path = parameter_geometry["panels"][first_panel]["mask"]

    y_minimum: int = (
        2
        * int(max(abs(parameter_pixelmaps["y"].max()), abs(parameter_pixelmaps["y"].min())))
        + 2
    )
    x_minimum: int = (
        2
        * int(max(abs(parameter_pixelmaps["x"].max()), abs(parameter_pixelmaps["x"].min())))
        + 2
    )
    parameter_data_shape: Tuple[int, ...] = parameter_pixelmaps["x"].shape
    parameter_visual_img_shape: Tuple[int, int] = (y_minimum, x_minimum)
    parameter_img_center_x: int = int(parameter_visual_img_shape[1] / 2)
    parameter_img_center_y: int = int(parameter_visual_img_shape[0] / 2)
    parameter_visual_pixelmap_x: NDArray[numpy.int32] = cast(
        NDArray[numpy.int32],
        numpy.array(parameter_pixelmaps["x"], dtype=numpy.int32)
        + parameter_visual_img_shape[1] // 2
        - 1,
    )
    parameter_visual_pixelmap_y: NDArray[numpy.int32] = cast(
        NDArray[numpy.int32],
        numpy.array(parameter_pixelmaps["y"], dtype=numpy.int32)
        + parameter_visual_img_shape[0] // 2
        - 1,
    )
    
    
    return parameter_visual_pixelmap_x, parameter_visual_pixelmap_y, parameter_visual_img_shape


def single_file_processing(input_file, h5path, output_folder, parameter_visual_pixelmap_x, parameter_visual_pixelmap_y, parameter_visual_img_shape, correct_enumarate):
    the_second_file = input_file.replace('_m01_', '_m02_') if '_m01_' in os.path.basename(input_file) else input_file.replace('_m02_', '_m01_')
    first_part_data = h5.File(input_file, 'r')[h5path]
    second_part_data = h5.File(the_second_file, 'r')[h5path]
    N = first_part_data.shape[0]
    
    images =  cast(
            NDArray[numpy.int_],
            numpy.concatenate(
                (
                    first_part_data, second_part_data
                    
                ), axis=1
            ),
        )
    

    frame_data_img: NDArray[Any] = numpy.full(parameter_visual_img_shape, -1., dtype=numpy.int32)
    
    print(f'{input_file} has {images.shape[0]} number of frames in total')
    for idx in range(0, images.shape[0]):
        frame_data_img[parameter_visual_pixelmap_y.ravel(), parameter_visual_pixelmap_x.ravel()] = images[idx,:].ravel()
        prefix = os.path.basename(input_file).split('.')[0]
        
        cbf = fabio.cbfimage.cbfimage(data=frame_data_img[()])
        fname = os.path.join(output_folder, f"{prefix}_%06i.cbf"%(idx+correct_enumarate))
        fname = re.sub(r"_part000\d+_", "_part00000_", fname)
        cbf.write(fname)
        
    return correct_enumarate+images.shape[0]


    
if __name__ == "__main__":
    
    args = parse_cmdline_args()
    
    dirpath = args.d #/asap3/petra3/gpfs/p09/2022/data/11013673/raw/lysozyme_grid/grid_fly_001
    raw_directory = args.r
    if args.h5p is None:
        h5path = "/entry/instrument/detector/data"
    else:
        h5path = args.h5p
        
    output_folder = args.o #/gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/rotational/converted/lysozyme_grid/grid_fly_001
    geometry_input_file = args.g
    
    #Retrieve info from geometry file
    geometry_lines = open(geometry_input_file, 'r').readlines()
    parameter_visual_pixelmap_x, parameter_visual_pixelmap_y, parameter_visual_img_shape = load_geometry(geometry_lines)
    
    
    input_files = glob.glob(os.path.join(dirpath, '*_m01*'))
    correct_enumarate = 0
    print(f'Directory {dirpath} is processing')
    for input_file in input_files:
        correct_enumarate = single_file_processing(input_file, h5path, output_folder, parameter_visual_pixelmap_x,\
                                                   parameter_visual_pixelmap_y, parameter_visual_img_shape, correct_enumarate)
    
 