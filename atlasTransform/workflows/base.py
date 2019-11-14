from argparse import ArgumentParser
from bids import BIDSLayout
from nipype import Workflow
import sys
import os
from copy import deepcopy
from niworkflows.utils.misc import fix_multi_T1w_source_name

from nipype import __version__ as nipype_ver
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from niworkflows.interfaces.bids import (
    BIDSInfo
)

from ..workflows.datasink import init_datasink_wf
from ..utils.bids import collect_data, BIDSPlusDataGrabber

from ..workflows.atlasTransformWorkflow import init_atlas_transform_workflow

from ..interfaces import SubjectSummary, AboutSummary, DerivativesDataSink
from ..__about__ import __version__


def init_base_wf(opts: ArgumentParser,
                 layout: BIDSLayout,
                 run_uuid: str,
                 subject_list: list,
                 work_dir: str,
                 output_dir: str):
    workflow = Workflow(name='atlasTransform_wf')
    workflow.base_dir = opts.work_dir

    reportlets_dir = os.path.join(opts.work_dir, 'reportlets')
    for subject_id in subject_list:
        single_subject_wf = init_single_subject_wf(
            opts=opts,
            layout=layout,
            run_uuid=run_uuid,
            work_dir=str(work_dir),
            output_dir=str(output_dir),
            name="single_subject_" + subject_id +"_wf",
            subject_id=subject_id,
            reportlets_dir=reportlets_dir,
        )

        single_subject_wf.config['execution']['crashdump_dir'] = (
            os.path.join(output_dir, "atlasTransform", "sub-" + subject_id, 'log', run_uuid)
        )
        for node in single_subject_wf._get_all_nodes():
            node.config = deepcopy(single_subject_wf.config)

        workflow.add_nodes([single_subject_wf])

    return workflow


def init_single_subject_wf(
            opts: ArgumentParser,
            layout: BIDSLayout,
            run_uuid: str,
            work_dir:str,
            output_dir:str,
            name:str,
            subject_id:str,
            reportlets_dir:str,
):
    import nilearn
    if name in ('single_subject_wf', 'single_subject_test_wf'):
        # for documentation purposes
        subject_data = {
            'bold': ['/completely/made/up/path/sub-01_task-nback_bold.nii.gz']
        }
    else:
        subject_data = collect_data(layout, subject_id, None)[0]

    workflow = Workflow(name=name)
    workflow.base_dir = work_dir
    workflow.__desc__ = """
    Results included in this manuscript come from processing
    performed using *atlasTransform* {atlasTransform_ver}
    (@atlasTransform1; @atlasTransform; RRID:some.id),
    which is based on *Nipype* {nipype_ver}
    (@nipype1; @nipype2; RRID:SCR_002502).
    """.format(atlasTransform_ver=__version__, nipype_ver=nipype_ver)
    workflow.__postdesc__ = """
    Many internal operations of *atlasTransform* use
    *Nilearn* {nilearn_ver} [@nilearn, RRID:SCR_001362].
    ### Copyright Waiver
    The above boilerplate text was automatically generated by fMRIPrep
    with the express intention that users should copy and paste this
    text into their manuscripts *unchanged*.
    It is released under the [CC0]\
    (https://creativecommons.org/publicdomain/zero/1.0/) license.
    ### References
    """.format(nilearn_ver=nilearn.version.__version__)

    inputnode = pe.Node(niu.IdentityInterface(fields=['subjects_dir']),
                        name='inputnode')
    #
    # # require_masks = opts.source_format == 'bold'
    # bidssrc = pe.Node(BIDSPlusDataGrabber(subject_data=subject_data, require_masks=False),
    #                   name='bidssrc')
    #
    # # bids_info = pe.Node(BIDSInfo(
    # #     bids_dir=layout.root, bids_validate=False), name='bids_info')
    #
    # summary = pe.Node(SubjectSummary(),
    #     name='summary', run_without_submitting=True)
    #
    # about = pe.Node(AboutSummary(version=__version__,
    #                              command=' '.join(sys.argv)),
    #                 name='about', run_without_submitting=True)
    #
    # ds_report_summary = pe.Node(
    #     DerivativesDataSink(base_directory=reportlets_dir,
    #                         desc='summary', keep_dtype=True),
    #     name='ds_report_summary', run_without_submitting=True)
    #
    # ds_report_about = pe.Node(
    #     DerivativesDataSink(base_directory=reportlets_dir,
    #                         desc='about', keep_dtype=True),
    #     name='ds_report_about', run_without_submitting=True)

    # Preprocessing of T1w (includes registration to MNI)

    # workflow.connect([
    #     # (bidssrc, bids_info, [('bold', 'in_file')]),
    #     (inputnode, summary, [('subjects_dir', 'subjects_dir')]),
    #     (bidssrc, summary, [('t1w', 't1w'),
    #                         ('t2w', 't2w'),
    #                         ('bold', 'bold')]),
    #     # (bids_info, summary, [('subject', 'subject_id')]),
    #     (bidssrc, ds_report_summary, [('bold', 'source_file')]),
    #     # (summary, ds_report_summary, [('out_report', 'in_file')]),
    #     (bidssrc, ds_report_about, [('bold', 'source_file')]),
    #     (about, ds_report_about, [('out_report', 'in_file')]),
    # ])

    # Overwrite ``out_path_base`` of smriprep's DataSinks
    for node in workflow.list_node_names():
        if node.split('.')[-1].startswith('ds_'):
            workflow.get_node(node).interface.out_path_base = 'atlasTransform'

    for i in range(len(subject_data['bold'])):
        transform_wf = init_atlas_transform_workflow(
            nifti=subject_data['bold'][i],
            atlas_name=opts.atlas_name,
            options=opts,
            name='atlas_transform_%d_wf' % i
        )
        # workflow.connect([
        #     (inputnode, transform_wf, [('subjects_dir', 'inputnode.subjects_dir')]),
        # ])

        outputs_wf = init_datasink_wf(bids_root=str(layout.root), output_dir=str(opts.output_dir), atlas_name=opts.atlas_name, name='ds_%d_wf' % i)

        workflow.connect([(transform_wf,outputs_wf,[('outputnode.transformed','inputnode.source_file')])])
        # outputs_wf.inputs.source_file = subject_data['csv'][i] if subject_data.__contains__('mask') else subject_data['bold'][i]

        workflow.connect([(transform_wf, outputs_wf, [
            ('outputnode.transformed', 'inputnode.transformed')
        ])])

    return workflow


def _prefix(subid):
    if subid.startswith('sub-'):
        return subid
    return '-'.join(('sub', subid))


def _pop(inlist):
    if isinstance(inlist, (list, tuple)):
        return inlist[0]
    return inlist