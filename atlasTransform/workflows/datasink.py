from smriprep.workflows.outputs import _bids_relative
from nipype import Workflow
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from ..interfaces import DerivativesDataSink

DEFAULT_MEMORY_MIN_GB=0.01


def init_datasink_wf(bids_root: str, output_dir: str, atlas_name: str, name='datasink_wf'):
    workflow = Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=[
        'transformed', 'source_file']),
        name='inputnode')

    raw_sources = pe.Node(niu.Function(function=_bids_relative), name='raw_sources')
    raw_sources.inputs.bids_root = bids_root

    ds_transform = pe.Node(DerivativesDataSink(
        base_directory=output_dir),
        name="ds_transform", run_without_submitting=True,
        mem_gb=DEFAULT_MEMORY_MIN_GB)
    workflow.connect([
        (inputnode, raw_sources, [('source_file', 'in_files')]),
        (inputnode, ds_transform, [('source_file', 'source_file'),
                                   ('transformed', 'in_file'),
                               ])
    ])

    return workflow