#!/usr/bin/env python
import os
import shutil
import numpy as np
import warnings
import argparse
import json
from pymatgen.core.structure import Structure
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.inputs import Potcar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.periodic_table import Element
#import atom
from copy import deepcopy
import itertools as it
import sys
import re
import ruamel.yaml as yaml

#import parse_poscar as ppos
#import pydefect.input_generator.defect_input.DefectSetting as DefectSetting 

__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2017, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "December 4, 2017"


SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pydefect.yaml")

def normed_random_3D_vector():
    """
    Generates a random 3D unit vector with a uniform spherical distribution.
    stackoverflow.com/questions/5408276/python-uniform-spherical-distribution
    """
    phi = np.random.uniform(0, np.pi*2)
    costheta = np.random.uniform(-1, 1)
    theta = np.arccos(costheta)
    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)
    return np.array([x, y, z])

def random_vector(normed_vector, distance):
    """
    Return a vector scaled by distance * x, where 0<x<1.

    Args:
        normed_vector (3x1 array): Normed 3D vector.
        distance (float): distance
    """
    return normed_vector * distance * np.random.random()

def perturb_around_a_point(structure, center, cutoff, distance):
    """
    Randomly perturb atoms around an input point in a structure.

    Args:
        center (3x1 array): Fractional coordinates of a central position.
        cutoff (float): Radius of a sphere in which atoms are perturbed [A]. 
        distance (float): Max distance for the perturbation [A].
    """

    if  type(center) == list and len(center) == 3:
        cartesian_coords = structure.lattice.get_cartesian_coords(center)
        neighbors = structure.get_sites_in_sphere(
                                  cartesian_coords, cutoff, include_index=True)
    else:
        raise ValueError
    sites = []
    # Since translate_sites accepts only one vector, we need to iterate this.
    for i in neighbors:
        vector = random_vector(normed_random_3D_vector(), distance)
        site = i[2]
        sites.append(site)
        structure.translate_sites(site, vector, frac_coords=False)

    return {"structure": structure, "sites": sites}


def potcar_dir():
    """    
    Return the name of POTCAR file directory.
    SETTINGS_FILE needs to be defined in the same module.
    """    
    try:
        with open(SETTINGS_FILE, "rt") as f:
            d = yaml.safe_load(f)
    except:
        raise IOError('.pydefect.yaml cannot be opened.')

    for k, v in d.items():
        if k == "DEFAULT_POTCAR":
            potcar_dir = v

    if not potcar_dir:
        raise ValueError('DEFAULT_POTCAR is not set in .pydefect.yaml')

    return potcar_dir

def make_POTCAR(dirname, elements, default_potcar_dir):
    """    
    Write POTCAR with a sequence of given elements names at *dirname*.
    So far, only default POTCAR files are supported.    
    """    
    with open(dirname + '/POTCAR', 'w') as potcar:
        for e in elements:
            potcar_file_name = default_potcar_dir + "/POTCAR_" + e
            with open(potcar_file_name) as pot:
                potcar.write(pot.read())

def _get_int_from_string(x):
    """ return int number only """
    return int(''.join(i for i in x if i.isdigit() or i == '.'))


def _defect_name(defect_name):
    try:
        d = defect_name.split("_")
        in_name = d[0]
        out_name = d[1]
        charge = int(d[2])
    except:
        raise ValueError("Defect {} is improper.", defect_name)

    if not re.match(r'^[a-xA-Z]+[1-9]+$',out_name):
        raise ValueError("Defect {} is improper.", defect_name)

    return (in_name, out_name, charge)

def get_elements_nions(defect_structure):
    elements, nions = defect_structure.to(fmt="poscar").split("\n")[5:7]
    elements = elements.split()
    nions = [int(i) for i in nions.split()]
    return elements, nions

def get_charge(potcar, nions, charge):
    """
    """
    p = Potcar.from_file(potcar)
    # check only the length of potcar and nions.
    if not len(p) == len(nions):
        raise ValueError("Size of elements in POTCAR file is different")
    nelect = sum([v.nelectrons * nions[i] for i, v in enumerate(p)]) - charge
    return nelect        

class VaspInputMaker():
    """
    Construct a set of vasp input files.
    POTCAR files are fetched from ~/.pydefect.yaml.
    
    Args:
        defect_setting: DefectSetting class object
        defect_name (str): defect name defined in PyDefect, e.g., "Va_Mg1_2"
        poscar (str): DPOSCAR name
        incar (str): INCAR name
        kpoints (str): KPOINTS name
    
    """

    def __init__(self, defect_name, defect_setting, incar="INCAR", kpoints="KPOINTS"):

        if os.path.exists(defect_name):
            self.is_directory = True
        else:
            os.makedirs(defect_name)
            self.is_directory = False
            self.defect_name = defect_name
            self.defect_setting = defect_setting
            self.incar = incar
            self.kpoints = kpoints
            self.in_name, self.out_name, self.charge = _defect_name(defect_name)
            # deepcopy is needed for structure
            self.defect_structure = deepcopy(defect_setting.structure)
    
            # e.g., irrep_element_names = ["Mg1", "O1"]
            self.irrep_element_names = [irrep_element.irrepname 
                       for irrep_element in self.defect_setting.irrep_elements]
    def constructor(self):
        # out 
        if re.match(r'^i[0-9]+$', self.out_name):
            interstitial_index = _get_int_from_string(self.out_name)
            try:
                defect_coords = \
                self.defect_setting.interstitial_coords[interstitial_index - 1]
            except:
                raise ValueError(
                 "Interstitial # {} is not defined".format(interstitial_index))
        elif self.out_name in self.irrep_element_names:
            for irrep_element in self.defect_setting.irrep_elements:
                if self.out_name == irrep_element.irrepname:
                    removed_atomic_index = irrep_element.first_index
                    defect_coords = irrep_element.repr_coord
            self.defect_structure.remove_sites([removed_atomic_index - 1])
        else:
            raise ValueError("{} is improper.".format(self.out_name))

        # in
        # defect_position means fractional coordinates  for vacancy and 
        # atomic index for substitutionals and interstitials.
        if self.in_name == "Va":
            if not removed_atomic_index:
                raise ValueError("{} is improper.".format(self.out_name))
            self.defect_position = defect_coords
        elif Element.is_valid_symbol(self.in_name):
            # There may be multiple candidate for inserted element.
            # E.g., Mg exists in Mg1 and Mg2.
            # Atom is inserted just before the same elements, 
            # but foreign atom is inserted first.
            candidate_atomic_indices = []
            for irrep_element in self.defect_setting.irrep_elements:
                if self.in_name == irrep_element.element:
                    candidate_atomic_indices.append(irrep_element.first_index)
            if candidate_atomic_indices == []:
                atomic_index = 1
            else:
                atomic_index = min(candidate_atomic_indices)
            self.defect_structure.insert(atomic_index - 1, self.in_name, 
                                                                 defect_coords)
            self.defect_position = atomic_index
        else:
            raise ValueError("{} is improper.".format(self.in_name))

        # write a defect position to defect.json file.
        f = open(self.defect_name + "/defect.json", 'w')
        json.dump({"defect_position": self.defect_position}, f, indent=2)

        self.defect_structure.to(filename=self.defect_name + "/POSCAR-Initial")

        # randomly perturb neighboring atoms.
        if self.defect_setting.displace is not None: 
            a = perturb_around_a_point(self.defect_structure, defect_coords, 
                      self.defect_setting.cutoff, self.defect_setting.displace)
            self.defect_structure = a["structure"]
            self.perturbed_sites = a["sites"]
        
        self.defect_structure.to(filename=self.defect_name + "/POSCAR-DispInitial")
        self.defect_structure.to(filename=self.defect_name + "/POSCAR")

        elements, nions = get_elements_nions(self.defect_structure)

        # Construct POTCAR file
        make_POTCAR(self.defect_name, elements, potcar_dir()) 
        # Construct INCAR file
        shutil.copyfile(self.incar, self.defect_name + "/INCAR")
        nelect = get_charge(self.defect_name + "/POTCAR", nions, self.charge)
        with open(self.defect_name + '/INCAR', 'a') as i:
            i.write('NELECT = ' + str(nelect))
        # Construct KPOINTS file
        shutil.copyfile(self.kpoints, self.defect_name + "/KPOINTS")


class VaspInputSetMaker():

    def __init__(self, defect_setting, incar="INCAR", kpoints="KPOINTS"):

        self.defect_setting = defect_setting
        self.incar = incar
        self.kpoints = kpoints

        # perfect
        if os.path.exists("perfect"):
            raise FileExistsError('perfect exists, so do nothing for this.')
        else:
            os.makedirs("perfect")
            self.defect_setting.structure.to(filename="perfect/POSCAR")
            shutil.copyfile(self.incar, "perfect/INCAR")
            shutil.copyfile(self.kpoints, "perfect/KPOINTS")
            elements, nions = get_elements_nions(self.defect_setting.structure)
            make_POTCAR("perfect", elements, potcar_dir()) 

        self.defect_names = []
        # vacancies          
        for i in self.defect_setting.irrep_elements:
            print(i.element)
            print(oxidation_states[i.element])
#            for j in range(oxidation_states[i.element]):
#                self.defect_names.append("Va_" + i.irrepname + "_" + j)
