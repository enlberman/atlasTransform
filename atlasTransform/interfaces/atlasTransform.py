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


def _bold_native_masked_derivative(bold_img, mask_img, derivative_data, out_file):
    from nilearn.image import index_img
    bold_template = index_img(bold_img, 0)
    template_data = bold_template.get_data()
    mask = mask_img.get_data() == 1
    template_data[~mask] = 0
    template_data[mask] = derivative_data
    bold_template.__class__(template_data, bold_template.affine, bold_template.header).to_filename(out_file)


def _reslice_to_atlas(atlas, img_3d):
    return nilearn.image.resample_img(img_3d, atlas.affine, atlas.shape)


def _roi_ts(img_list_atlas_space, atlas_data, j):
    return [(img_list_atlas_space[i].get_data() * (atlas_data == j)).mean() for i in
            range(len(img_list_atlas_space))]


class AtlasTransform(SimpleInterface):
    """

    """
    input_spec = AtlasTransformInputSpec
    output_spec = AtlasTransformOutputSpec

    def _run_interface(self, runtime):
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
        source_dimensions = len(source_img.shape)
        target_affine = source_img.affine

        if source_dimensions == 4:
            source_img = nibabel.four_to_three(source_img)
            target_affine = source_img[0].affine
        else:
            source_img = [source_img]

        atlas = nilearn.image.resample_img(atlas, target_affine=target_affine, interpolation='nearest')
        atlas_data = atlas.get_data()
        atlas_labels = numpy.unique(atlas_data).astype('int16')

        rois = partial(_roi_ts, source_img, atlas_data)
        timeseries_roi_data = [rois(i) for i in atlas_labels]
        suffix = "_%s.csv" % atlas_name
        if source_dimensions == 4:
            suffix = suffix.replace('.csv', 'ts.csv')

        out_file = fname_presuffix(self.inputs.nifti, suffix=suffix, newpath=os.getcwd(), use_ext=False)
        numpy.savetxt(out_file, numpy.vstack(timeseries_roi_data), delimiter=',')

        self._results['transformed'] = out_file

        return runtime
