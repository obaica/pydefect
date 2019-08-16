# -*- coding: utf-8 -*-
import re
from typing import Union

from monty.json import MSONable

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"


class DefectName(MSONable):
    def __init__(self,
                 name: str,
                 charge: int,
                 annotation: str = None):

        self.name = name
        self.charge = charge
        self.annotation = annotation

    @property
    def name_str(self):
        return self.name

    def is_name_matched(self,
                        keywords: Union[str, list, None]):
        """ Return True if name is matched by the selected_keywords.

        Args:
            keywords (str/list): Keywords used for checking if name is selected.

        When the following type names are given, constructs a set of defects.
            "Va"    --> A set of all the vacancies.
            "_i"     --> A set of all the interstitials.
            "Va_O"  --> A set of all the oxygen vacancies
            "Va_O[0-9]+_0" --> All the oxygen vacancies in neutral charge states
            "Va_O1" --> A set of oxygen vacancies at O1 site
            "Mg_O"  --> A set of all the Mg-on-O antisite pairs.
            "Mg_O1" --> A set of Mg-on-O1 antisite pairs.

        When complete defect_name is given, constructs a particular defect.
            e.g., "Va_O1_2",  "Mg_O1_0"
        """
        if keywords is None:
            return True

        try:
            if isinstance(keywords, str):
                keywords = [keywords]
        except TypeError:
            print(f"The type of keywords {keywords} is invalid.")

        return any([re.search(p, str(self)) for p in keywords])

    def __str__(self):
        if self.annotation:
            return "_".join([self.name_str, str(self.charge), self.annotation])
        else:
            return "_".join([self.name_str, str(self.charge)])

    def __repr__(self):
        annotation = "None" if self.annotation is None else self.annotation

        outs = ["DefectName Summary",
                "Name: " + self.name_str,
                "Charge: " + str(self.charge),
                "Annotation" + annotation]
        return "\n".join(outs)

    def __eq__(self, other):
        # Note: charge is not compared
        if isinstance(other, str):
            return True if self.__repr__() == other else False
        elif isinstance(other, DefectName):
            return True if self.__repr__() == other.__repr__() else False
        else:
            raise TypeError(
                "{} is not supported for comparison.".format(type(other)))

    def __hash__(self):
        return hash(self.name_str)

    @classmethod
    def from_str(cls, string):
        s = string.split("_")
        try:
            charge = int(s[-1])
            name = "_".join(s[:-1])
            return cls(name=name, charge=charge, annotation=None)
        except ValueError:
            charge = int(s[-2])
            name = "_".join(s[:-2])
            annotation = s[-1]
            return cls(name=name, charge=charge, annotation=annotation)


