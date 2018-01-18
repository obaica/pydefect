#!/bin/env python3                                                                                                                       

import sys
import os
import shutil
import glob
import argparse
import numpy as np
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.core import Structure
from pymatgen.io.vasp.outputs import Outcar
import json
from monty.json import MontyEncoder
from itertools import product

def append_to_json(file_path, key, val):
    print("append_to_json")
    print(file_path)
    print(os.path.exists(file_path))
    with open(file_path) as f:
        d = json.load(f)
    print(d)
    if key in d:
        raise ValueError(f"Key( {key} ) is already in file( {file_path} )")
    d[key] = val
    backup_path = file_path + "._backup_by_analyze_defect_py"
    shutil.copy(file_path, backup_path)
    os.remove(file_path)
    fw = open(file_path, 'w')
    json.dump(d, fw, indent=2, cls=MontyEncoder)
    os.remove(backup_path)

def add_refpot_to_json(outcar_path, json_path):
    try:
        outcar = Outcar(outcar_path)
    except:
        print("Failed to read reference potential.\
               Specify OUTCAR of perfect structure by -p option.")
        sys.exit()
        print("read_reference pot") 
    ref_pot = outcar.electrostatic_potential
    append_to_json(json_path, "reference_potential", ref_pot)
    print(ref_pot)

def calc_min_distance_and_its_v2coord(v1, v2, axis):
    neighbor = (-1, 0, 1)
    candidate_list = []
    for x, y, z in product(neighbor, repeat=3):
        delta_vect = np.dot(axis, np.array([x, y, z]))
        distance = np.linalg.norm(delta_vect+v2-v1)
        candidate_list.append((distance, delta_vect+v2))
    return min(candidate_list, key = lambda t: t[0])

def complete_defect_json(dirname):
    outcar = Outcar(dirname + "/OUTCAR-final")
    total_energy = outcar.final_energy
    poscar_initial = Poscar.from_file(dirname + "/POSCAR-initial")
    poscar_final = Poscar.from_file(dirname + "/POSCAR-final")
    coords_initial = poscar_initial.structure.cart_coords
    coords_final = poscar_final.structure.cart_coords
    elements = [e.name for e in poscar_final.structure.species]
    axis = poscar_initial.structure.lattice.matrix
    axis_inv = np.linalg.inv(axis)
    with open(dirname+"/defect.json") as f:
        d = json.load(f)
    defect_pos_frac = d["defect_position"]
    defect_pos = np.dot(axis, np.array(d["defect_position"]))
    print(defect_pos)
    distance_list, angle_list = [], []
    with open(dirname+"/structure.txt", 'w') as f:
        f.write("#Defect position (frac)\n")
        f.write(f"#{defect_pos_frac[0]: .6f} {defect_pos_frac[0]: .6f} {defect_pos_frac[0]: .6f}\n")
        f.write("#" + " " * 8  + "-" * 5 + "coordinations (frac)" + "-" * 5 + " " * 3 +"dist.(init)[A]" + " " * 3 + "dist.(final)[A]  disp.[A]  angle[deg.]\n")
        for i, (vi, vf, e) in enumerate(zip(coords_initial, coords_final, elements)): # calculate displacement, distance_from_defect, angle
#To calculate displacement, it is sometimes needed to find atoms in neighbor atoms
#due to periodical boundary condition.
#For example, initial position is (0,0,0) can be displaced to (0.99,0.99,0.99).
#Then it is needed to calculate distance between (0,0,0) and (-0.01,-0.01,-0.01).
            disp, neighbor_vf = calc_min_distance_and_its_v2coord(vi, vf, axis)
            distance_init, _ = calc_min_distance_and_its_v2coord(defect_pos, vi, axis)
            distance, _ = calc_min_distance_and_its_v2coord(defect_pos, vf, axis)
            if disp >= 0.1:
            #if disp >= 0:
                v1 = defect_pos - vi
                v2 = neighbor_vf - vi
                cosine = np.dot(v1, v2)/(np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = 180 - np.degrees(np.arccos(np.clip(cosine, -1, 1)))
            else:
                angle = "-"
            ne_vf_frac = np.round(np.dot(axis_inv, neighbor_vf),6)
            f.write(f"{e:3s} {str(i+1).rjust(3)}  {ne_vf_frac[0]: .5f}   {ne_vf_frac[1]: .5f}   {ne_vf_frac[2]: .5f}\
       {distance_init:.3f}            {distance:.3f}         {disp:.3f}         {angle}\n")






if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--all", action="store_true",
                        help="All procedure mode. (try 4.a-1, 4.a-2, and 4.a-3 of README.txt)")
    parser.add_argument("-r", "--reference_pot", action="store_true",
                        help="Reference_pot mode.\
                              Add a reference potential of perfect supercell to correction.json with\
                              (4.a-1 in README.txt)")
    parser.add_argument("-p", "--perfect_ref", dest="perfect_dir", type=str, default="perfect",
                        help="Directry name of calculation of perfect structure for reference.\
                              Used to add a reference potential of perfect supercell \
                              to correction.json with, and calculation of atomic displacement. \
                              (4.a-1, 2 in README.txt)")
    parser.add_argument("-i", "--info_defect", action="store_true",
                        help="Information_of_defect mode.\
                              Construct a full information JSON file(defect.json) of \
                              the defect in each directory.\
                              (4.a-2 in README.txt)")
    parser.add_argument("-v", "--visualize_structure", action="store_true",
                        help="Visualize_structure mode.\
                              Make local structure files for visualization.\
                              (4.a-3 in README.txt)")
    parser.add_argument("-d", "--defect_dir", dest="defect_dir", type=str,
                        help="Directry name of calculation of structure with defect.\
                              If you want to analyze one of defect calculations, specify with this option.\
                              Otherwise, procedure will done with all results of defect calculations.\
                              (4.a-2,3 in README.txt)")
    opts = parser.parse_args()
    if opts.all or opts.reference_pot:
        print("reference_pot mode")
        outcar_path = opts.perfect_dir + "/OUTCAR-final"
        json_path = "./correction.json"
        ref_pot = add_refpot_to_json(outcar_path, json_path)
    if opts.all or opts.info_defect:
        print("info_defect mode")
        if opts.defect_dir:
            complete_defect_json(opts.defect_dir)
        else:
            dirs = glob.glob("./defect/*_*_*/")
            if not dirs:
                print("Warning: No directory matched name defect_*_*_*.")
            for dirname in dirs:
                print(dirname)
                #dirname = os.path.abspath(dirname)
                complete_defect_json(dirname)
    if opts.all or opts.visualize_structure:
        pass
        #visualize_structure()
        
    

