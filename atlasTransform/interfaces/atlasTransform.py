from functools import partial

from nipype.interfaces.base import (
    traits, TraitedSpec, BaseInterfaceInputSpec, SimpleInterface,
    File, InputMultiPath, OutputMultiPath)
from nipype import logging
from python_fractal_scaling.dfa import dfa
import pandas
import numpy
import nibabel
import nilearn
import os
from nipype.utils.filemanip import fname_presuffix
from ..utils.atlas import load_craddock_2011, load_shen_268

LOGGER = logging.getLogger('nipype.interface')


class AtlasTransformInputSpec(TraitedSpec):
    nifti = traits.File(mandatory=True, desc='input nifti')
    atlas_name = traits.String(mandatory=True, desc='atlas nam')
    resolution = traits.Int(mandatory=False, desc='resolution (for shen atlas)')
    number_of_clusters = traits.Int(mandatory=False, desc='for craddock')
    similarity_measure = traits.String(mandatory=False, desc='for craddock')
    algorithm = traits.String(mandatory=False, desc='for craddock')


class AtlasTransformOutputSpec(TraitedSpec):
    out_report = File(exists=True, desc='conformation report')
    transformed = File(exists=True, desc='atlas file')
    confidence_intervals = File(exists=False, desc='confidence interval file')


def _roi_mean(img_list_atlas_space, atlas_data, j):
    """
    Average all the data in an roi.
    """
    return [
        (img_list_atlas_space[i].get_data() * (atlas_data == j)).mean()
        for i in range(len(img_list_atlas_space))
    ]


def _roi_error_propagation(img_list_atlas_space, atlas_data, j):
    """
    If X = sum(x_i)/n, i = 1,...,n
    then dX = sqrt(sum(dx_i**2))/n, i=1,...,n
    """
    return [
        numpy.sqrt(numpy.power(img_list_atlas_space[i].get_data() * (atlas_data == j), 2.0).sum()) / float(sum(atlas_data == j))
        for i in range(len(img_list_atlas_space))
    ]


class AtlasTransform(SimpleInterface):
    """

    """
    input_spec = AtlasTransformInputSpec
    output_spec = AtlasTransformOutputSpec

    def _run_interface(self, runtime):
        """Load the atlas and make the atlas name for the output file"""
        if self.inputs.atlas_name == 'shen':
            atlas = load_shen_268(resolution=self.inputs.resolution)
            atlas_name = self.inputs.atlas_name
        elif self.inputs.atlas_name == 'craddock':
            atlas = load_craddock_2011(
                number_of_clusters=self.inputs.number_of_clusters,
                algorithm=self.inputs.algorithm,
                similarity_measure=self.inputs.similarity_measure
            )
            atlas_name = "%s_%d" % (self.inputs.atlas_name, self.inputs.number_of_clusters)
        else:
            raise RuntimeError("Atlas name %s not recognized" % self.inputs.atlas_name)

        source_img = nibabel.load(self.inputs.nifti)
        source_dimensions = len(source_img.shape)  # 4D or 3D

        if source_dimensions == 4:
            source_img = nibabel.four_to_three(source_img)  # split the 4D image into a list of 3D volumes
        else:
            source_img = [source_img]

        target_affine = source_img[0].affine  # we need the affine from any of the 3d volumes
        target_shape = source_img[0].shape  # we need the affine from any of the 3d volumes

        atlas = nilearn.image.resample_img(atlas, target_affine=target_affine, target_shape=target_shape, interpolation='nearest')  # resample with nearest neighbor in case the atlas has a different resolution
        atlas_data = atlas.get_data()
        atlas_labels = numpy.unique(atlas_data).astype('int16')  # these need to be integers so we can use them to index matrices below

        rois = partial(_roi_mean, source_img, atlas_data)  # a closure of the _roi_ts function
        roi_data = [rois(i) for i in atlas_labels]  # average data in each roi

        suffix = "_%s.csv" % atlas_name
        if source_dimensions == 4:
            suffix = suffix.replace('.csv', 'ts.csv')  # 4D images get the ts suffix for time-series

        out_file = fname_presuffix(self.inputs.nifti, suffix=suffix, newpath=os.getcwd(), use_ext=False)
        numpy.savetxt(out_file, numpy.vstack(roi_data), delimiter=',')

        self._results['transformed'] = out_file

        return runtime
