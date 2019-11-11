#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Utilities to load atlases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
"""
import os
from pathlib import Path

import nibabel
from nipype import logging

LOGGER = logging.getLogger('nipype.interface')

CRADDOCK_CLUSTER_SIZES = [
    10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,
    350,400,450,500,550,600,650,700,750,800,850,900,950
]

def __get_data_folder_path():
    return os.path.join(Path(__file__).parent.parent.parent, 'data')


def load_shen_268(resolution: int) -> nibabel.Nifti1Image:
    """
    :param resolution: 2mm or 1 mm
    :return:
    """
    if not [1,2].__contains__(resolution):
        raise RuntimeError("%d is not a valid resolution for the shen atlas. Please use 1mm or 2mm" % resolution)

    atlas_path = os.path.join(__get_data_folder_path(), 'shen_268', 'shen_%dmm_268_parcellation.nii.gz' % resolution)
    return nibabel.load(atlas_path)


def load_craddock_2011(number_of_clusters: int, similarity_measure: str = 't', algorithm='2level') -> nibabel.Nifti1Image:
    """
    :param number_of_clusters: See the list of cluster sizes above or in volume_cluster_number.csv
    :param similarity_measure: t, s, or random (temporal, spatial, random)
    :param algorithm: 2level, mean, none
    :return:
    """
    if not ["t", "s", "random"].__contains__(similarity_measure):
        raise RuntimeError("%s is not a valid similarity measure for the craddock atlases. Please use 't', 's', 'random'" % similarity_measure)
    if not ["2level", "mean", None].__contains__(algorithm):
        raise RuntimeError(
            "%s is not a valid algorithm type for the craddock atlases. Please use '2level', 'mean', or None" % similarity_measure)
    if not CRADDOCK_CLUSTER_SIZES.__contains__(number_of_clusters):
        raise RuntimeError("%d is not a valid cluster size for the craddock atlases. Please use one of %s" % (number_of_clusters, str(CRADDOCK_CLUSTER_SIZES)))

    algorithm = algorithm + '_' if algorithm is not None else ''
    dataset_path = os.path.join(__get_data_folder_path(), 'craddock_2011', '%scorr05_%sall.nii.gz' % (similarity_measure, algorithm))
    dataset_img = nibabel.load(dataset_path)

    return nibabel.four_to_three(dataset_img)[CRADDOCK_CLUSTER_SIZES.index(number_of_clusters)]
