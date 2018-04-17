# -*- coding: utf-8 -*-

import json
import numpy as np
import os
import warnings

from monty.json import MontyEncoder
from monty.serialization import loadfn

from pymatgen.io.vasp.outputs import Outcar, Vasprun
from pymatgen.electronic_structure.core import Spin


__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2017, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "December 4, 2017"


class UnitcellDftResults:
    """
    DFT results for a unitcell
    Args:
        band_edge (1x2 list): VBM and CBM.
        band_edge2 (1x2 list, optional): Alternative VBM and CBM
        static_dielectric_tensor (3x3 numpy array):
        ionic_dielectric_tensor (3x3 numpy array):
        total_dos (2xN numpy array): [[energy1, dos1], [energy2, dos2],...]
    """

    def __init__(self, band_edge=None, band_edge2=None,
                 static_dielectric_tensor=None, ionic_dielectric_tensor=None,
                 total_dos=None):
        """ """
        self._band_edge = band_edge
#        self._band_edge2 = band_edge2
        self._static_dielectric_tensor = static_dielectric_tensor
        self._ionic_dielectric_tensor = ionic_dielectric_tensor
        self._total_dos = total_dos

    def __eq__(self, other):
        if other is None or type(self) != type(other):
            raise TypeError
        return self.__dict__ == other.__dict__

    def __str__(self):
        outs = ["vbm: " + str(self._band_edge[0]),
                "cbm: " + str(self._band_edge[1]),
                "static dielectric tensor:\n"
                                          + str(self._static_dielectric_tensor),
                "ionic dielectric tensor:\n" + str(self._ionic_dielectric_tensor),
                "total dielectric tensor:\n" + str(self.total_dielectric_tensor)]

        return "\n".join(outs)

    @classmethod
    def from_dict(cls, d):
        """
        Constructs a class object from a dictionary.
        """
#        return cls(d["band_edge"], d["band_edge2"],
        return cls(d["band_edge"],
                   d["static_dielectric_tensor"], d["ionic_dielectric_tensor"],
                   d["total_dos"])

    @classmethod
    def json_load(cls, filename):
        """
        Constructs a class object from a json file.
        """
        return cls.from_dict(loadfn(filename))

    # getter
    @property
    def band_edge(self):
        if self._band_edge is None:
            warnings.warn(message="Band edges are not set yet.")
            return None
        else:
            return self._band_edge

    # @property
    # def band_edge2(self):
    #     if self._band_edge2 is None:
    #         warnings.warn(message="Second band edges are not set yet.")
    #         return None
    #     else:
    #         return self._band_edge2

    @property
    def static_dielectric_tensor(self):
        if self._static_dielectric_tensor is None:
            warnings.warn(message="Static dielectric tensor is not set yet.")
            return None
        else:
            return self._static_dielectric_tensor

    @property
    def ionic_dielectric_tensor(self):
        if self._ionic_dielectric_tensor is None:
            warnings.warn(message="Ionic dielectric tensor is not set yet.")
            return None
        else:
            return self._ionic_dielectric_tensor

    @property
    def total_dielectric_tensor(self):
        if self._static_dielectric_tensor is None:
            warnings.warn(message="Static dielectric tensor is not set yet.")
            return None
        elif self._ionic_dielectric_tensor is None:
            warnings.warn(message="Ionic dielectric tensor is not set yet.")
            return None
        else:
            return self._static_dielectric_tensor + \
                   self._ionic_dielectric_tensor

    @property
    def total_dos(self):
        if self._total_dos is None:
            warnings.warn(message="Total density of states is not set yet.")
            return None
        else:
            return self._total_dos

    def is_set_all(self):
        #           self._band_edge2 is not None and \
        if self._band_edge is not None and \
           self._static_dielectric_tensor is not None and \
           self._ionic_dielectric_tensor is not None and \
           self._total_dos is not None:
            return True
        else:
            return False

    # setter
    @band_edge.setter
    def band_edge(self, band_edge):
        self._band_edge = band_edge

    # @band_edge2.setter
    # def band_edge2(self, band_edge2):
    #     self._band_edge2 = band_edge2

    @static_dielectric_tensor.setter
    def static_dielectric_tensor(self, static_dielectric_tensor):
        self._static_dielectric_tensor = static_dielectric_tensor

    @ionic_dielectric_tensor.setter
    def ionic_dielectric_tensor(self, ionic_dielectric_tensor):
        self._ionic_dielectric_tensor = ionic_dielectric_tensor

    @total_dos.setter
    def total_dos(self, total_dos):
        self._total_dos = total_dos

    # setter from vasp results
    def set_band_edge_from_vasp(self, directory_path,
                                vasprun_name="vasprun.xml"):
        vasprun = Vasprun(os.path.join(directory_path, vasprun_name))
        _, cbm, vbm, _ = vasprun.eigenvalue_band_properties
        self._band_edge = [vbm, cbm]

    # def set_band_edge2_from_vasp(self, directory_path,
    #                              vasprun_name="vasprun.xml"):
    #     vasprun = Vasprun(os.path.join(directory_path, vasprun_name))
    #     _, cbm, vbm, _ = vasprun.eigenvalue_band_properties
    #     self._band_edge2 = [vbm, cbm]

    def set_static_dielectric_tensor_from_vasp(self, directory_path,
                                               outcar_name="OUTCAR"):
        outcar = Outcar(os.path.join(directory_path, outcar_name))
        self._static_dielectric_tensor = np.array(outcar.dielectric_tensor)

    def set_ionic_dielectric_tensor_from_vasp(self, directory_path,
                                              outcar_name="OUTCAR"):
        outcar = Outcar(os.path.join(directory_path, outcar_name))
        self._ionic_dielectric_tensor = np.array(outcar.dielectric_ionic_tensor)

    def set_total_dos_from_vasp(self, directory_path,
                                vasprun_name="vasprun.xml"):
        vasprun = Vasprun(os.path.join(directory_path, vasprun_name))
        dos, ene = vasprun.tdos.densities, vasprun.tdos.energies
        # only non-magnetic
        self._total_dos = np.vstack([dos[Spin.up], ene])

    def as_dict(self):
        """
        Dict representation of DefectInitialSetting class object.
        """

#        "band_edge2":               self.band_edge2,
        d = {"band_edge":                self.band_edge,
             "static_dielectric_tensor": self.static_dielectric_tensor,
             "ionic_dielectric_tensor":  self.ionic_dielectric_tensor,
             "total_dos":                self.total_dos}

        return d

    def to_json_file(self, filename):
        """
        Returns a json file, named unitcell.json.
        """
        with open(filename, 'w') as fw:
            json.dump(self.as_dict(), fw, indent=2, cls=MontyEncoder)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--json_file", dest="json_file", default=None, type=str)
    parser.add_argument("--band_edge_dir", dest="band_edge_dir", default=None, type=str)
    parser.add_argument("--static_diele_dir", dest="static_diele_dir", default=None, type=str)
    parser.add_argument("--ionic_diele_dir", dest="ionic_diele_dir", default=None, type=str)
    parser.add_argument("--total_dos_dir", dest="total_dos_dir", default=None, type=str)

    opts = parser.parse_args()

    # if opts.json_file:
    #     try:
    #         dft_results = UnitcellDftResults.json_load(filename=opts.json_file)
    #     except IOError:
    #         print(opts.json_file, "does not exist.")
    # else:
    #     dft_results = UnitcellDftResults()
    dft_results = UnitcellDftResults()

    if opts.band_edge_dir:
        try:
            dft_results.set_band_edge_from_vasp(opts.band_edge_dir)
        except IOError:
            print(opts.band_edge_dir, "is not appropriate.")

    if opts.static_diele_dir:
        try:
            dft_results.\
                set_static_dielectric_tensor_from_vasp(opts.static_diele_dir)
        except IOError:
            print(opts.static_diele_dir, "is not appropriate.")

    if opts.ionic_diele_dir:
        try:
            dft_results.\
                set_ionic_dielectric_tensor_from_vasp(opts.ionic_diele_dir)
        except IOError:
            print(opts.ionic_diele_dir, "is not appropriate.")

    if opts.total_dos_dir:
        try:
            dft_results.set_total_dos_from_vasp(opts.total_dos_dir)
        except IOError:
            print(opts.total_dos_dir, "is not appropriate.")

    dft_results.to_json_file(opts.json_file)


if __name__ == "__main__":
    main()