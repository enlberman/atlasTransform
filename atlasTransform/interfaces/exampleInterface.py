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

LOGGER = logging.getLogger('nipype.interface')


class DFAInputSpec(TraitedSpec):
    bold = traits.File(mandatory=True, desc='input bold')
    brainmask = traits.String( mandatory=False, desc='brainmask in bold space')
    csv = traits.String(mandatory=False, desc='input csv')
    max_frequency = traits.Float(.1, usedefault=True,
                             desc='Maximum frequency')
    min_frequency = traits.Float(.01, usedefault=True,
                             desc='Minimum frequency')
    # output_format = traits.String('', usedefault=True,
    #                              desc='output format: default is the same as input format')

    drop_vols = traits.Int(5, usedefault=True,
                                  desc='how many volumes to drop')


class DFAOutputSpec(TraitedSpec):
    out_report = File(exists=True, desc='conformation report')
    hurst = File(exists=True, desc='hurst file')
    confidence_intervals = File(exists=True, desc='confidence interval file')
    rsquared = File(exists=True, desc='r squared file')


def _bold_native_masked_derivative(bold_img, mask_img, derivative_data, out_file):
    from nilearn.image import index_img
    bold_template = index_img(bold_img, 0)
    template_data = bold_template.get_data()
    mask = mask_img.get_data() == 1
    template_data[~mask] = 0
    template_data[mask] = derivative_data
    bold_template.__class__(template_data, bold_template.affine, bold_template.header).to_filename(out_file)


class DFA(SimpleInterface):
    """
    Finds template target dimensions for a series of T1w images, filtering low-resolution images,
    if necessary.

    Along each axis, the minimum voxel size (zoom) and the maximum number of voxels (shape) are
    found across images.

    The ``max_scale`` parameter sets a bound on the degree of up-sampling performed.
    By default, an image with a voxel size greater than 3x the smallest voxel size
    (calculated separately for each dimension) will be discarded.

    To select images that require no scaling (i.e. all have smallest voxel sizes),
    set ``max_scale=1``.
    """
    input_spec = DFAInputSpec
    output_spec = DFAOutputSpec

    def _run_interface(self, runtime):
        img = nibabel.load(str(self.inputs.bold))
        tr = img.header.get('pixdim')[4]

        use_bold = self.inputs.brainmask is not None

        if use_bold:
            mask_img = nibabel.load(str(self.inputs.brainmask))
            data = nilearn.masking.apply_mask(imgs=img,mask_img=mask_img).T
        else:
            data = pandas.read_csv(str(self.inputs.csv))

        data = data[:,self.inputs.drop_vols:].T

        mn = int(numpy.ceil(1 / (tr * self.inputs.max_frequency)))
        mx = int(numpy.floor(1 / (tr * self.inputs.min_frequency)))

        h, hci, rs = dfa(data, max_window_size=mx, min_widow_size=mn)
        hci = numpy.vstack(hci)

        if use_bold:
            out_hurst = fname_presuffix(self.inputs.bold, suffix='_hurst', newpath=os.getcwd())
            out_cis = fname_presuffix(self.inputs.bold, suffix='_hurst_ci', newpath=os.getcwd())
            out_r2s = fname_presuffix(self.inputs.bold, suffix='_hurst_r2', newpath=os.getcwd())

            _bold_native_masked_derivative(bold_img=img, mask_img=mask_img, derivative_data=h, out_file=out_hurst)
            _bold_native_masked_derivative(bold_img=img, mask_img=mask_img, derivative_data=hci[:,0], out_file=out_cis)
            _bold_native_masked_derivative(bold_img=img, mask_img=mask_img, derivative_data=rs, out_file=out_r2s)
        else:
            out_hurst = fname_presuffix(self.inputs.bold, suffix='_hurst.csv', use_ext=False)
            out_cis = fname_presuffix(self.inputs.bold, suffix='_hurst_ci.csv', use_ext=False)
            out_r2s = fname_presuffix(self.inputs.bold, suffix='_hurst_r2.csv', use_ext=False)

            numpy.savetxt(out_hurst, h, delimiter=',')
            numpy.savetxt(out_cis, hci, delimiter=',')
            numpy.savetxt(out_r2s, rs, delimiter=',')

        self._results['hurst'] = out_hurst
        self._results['confidence_intervals'] = out_cis
        self._results['rsquared'] = out_r2s

        return runtime
