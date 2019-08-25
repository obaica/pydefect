# -*- coding: utf-8 -*-

import filecmp
import tempfile
from collections import OrderedDict

from pydefect.core.complex_defects import ComplexDefect, ComplexDefects
from pydefect.util.testing import PydefectTest

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"


class ComplexDefectTest(PydefectTest):
    def setUp(self):
        self.mgo = ComplexDefect(removed_atom_indices=[4, 25],
                                 inserted_atoms=[{"element": "Cu",
                                                  "coords": [0.375, 0.5, 0.5]}],
                                 point_group="mm2",
                                 multiplicity=96,
                                 extreme_charge_state=3,
                                 annotation="test")

    def test_dict(self):
        d = self.mgo.as_dict()
        rounded_d = ComplexDefect.from_dict(d).as_dict()
        self.assertEqual(d, rounded_d)


class ComplexDefectsTest(PydefectTest):
    def setUp(self):
        self.structure = self.get_structure_by_name("Cu2O48atoms")

        split = ComplexDefect(removed_atom_indices=[4, 25],
                              inserted_atoms=[{"element": "Cu",
                                               "coords": [0.375, 0.5, 0.5]}],
                              point_group="mm2",
                              multiplicity=192,
                              extreme_charge_state=1)

        self.cu2o = \
            ComplexDefects(self.structure, OrderedDict({"split": split}))

    def test_dict(self):
        d = self.cu2o.as_dict()
        point_group = d["complex_defects"]["split"]["point_group"]
        self.assertEqual(point_group,"mm2")
        rounded_d = ComplexDefects.from_dict(d).as_dict()
        self.assertEqual(d, rounded_d)

    def test_yaml(self):
        tmp_file = tempfile.NamedTemporaryFile().name
        self.cu2o.site_set_to_yaml_file(tmp_file)
        self.assertTrue(filecmp.cmp("expected_complex_defects.yaml", tmp_file))

    def test_msonable(self):
        self.assertMSONable(self.cu2o)

    def test_from_files(self):
        actual = ComplexDefects.from_files(
            structure=self.structure,
            yaml_filename="expected_complex_defects.yaml").as_dict()
        expected = self.cu2o.as_dict()
        self.assertEqual(expected, actual)

    def test_add(self):
        self.cu2o.add_defect(removed_atom_indices=[0, 32],
                             inserted_atoms=[],
                             name="divacancy",
                             extreme_charge_state=1)

        print(self.cu2o.complex_defects["divacancy"])



