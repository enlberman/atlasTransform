from pathlib import Path

from nipype.interfaces.base import (
    traits, TraitedSpec, SimpleInterface,
    File)
from nipype import logging
import numpy
import nibabel
import nilearn
import nilearn.input_data
import os
from nipype.utils.filemanip import fname_presuffix
from ..utils.atlas import load_craddock_2011, load_shen_268, load_power

LOGGER = logging.getLogger('nipype.interface')


class AtlasTransformInputSpec(TraitedSpec):
    nifti = traits.Any(mandatory=True, desc='input nifti')
    atlas_name = traits.String(mandatory=True, desc='atlas name')
    bids_dir = traits.String(mandatory=True, desc='atlas name')
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
        (img_list_atlas_space[i].get_data() * (atlas_data == j)).sum() / (atlas_data == j).sum()
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
        elif self.inputs.atlas_name == 'power':
            atlas = load_power()
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

        if type(self.inputs.nifti) == list:
            self.inputs.nifti = self.inputs.nifti[0]
        source_img = nibabel.load(self.inputs.nifti)
        source_dimensions = len(source_img.shape)  # 4D or 3D
        if not self.inputs.atlas_name == 'power':
            masker = nilearn.input_data.NiftiLabelsMasker(atlas)
            roi_data = masker.fit_transform(source_img)
        else:
            masker = nilearn.input_data.NiftiSpheresMasker(atlas, radius=15, allow_overlap=True,smoothing_fwhm=6)
            roi_data = masker.fit_transform(source_img)
        suffix = "_%s.csv" % atlas_name
        if source_dimensions == 4:
            suffix = suffix.replace('.csv', '_ts.csv')  # 4D images get the ts suffix for time-series

        out_file = fname_presuffix(self.inputs.nifti, suffix=suffix, use_ext=False).replace(Path(self.inputs.bids_dir).stem,  __name__.split('.')[0])
        os.makedirs(Path(out_file).parent, exist_ok=True)
        numpy.savetxt(out_file, roi_data, delimiter=',')

        self._results['transformed'] = out_file

        return runtime
