from nipype.pipeline import engine as pe
from nipype.interfaces import (
    utility as niu,
)
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from ..interfaces import AtlasTransform


def init_atlas_transform_workflow(nifti, atlas_name, options, name='atlas_transform_wf'):

    workflow = Workflow(name=name)
    desc = """Transformation to atlas space
    : """

    inputnode = pe.Node(
        niu.IdentityInterface(fields=['nifti','atlas_name', 'resolution', 'number_of_clusters', 'similarity_measure', 'algorithm']),
        name='inputnode')

    inputnode.inputs.nifti = nifti
    inputnode.inputs.atlas_name = atlas_name
    inputnode.inputs.resolution = options.resolution
    inputnode.inputs.number_of_clusters = options.number_of_clusters
    inputnode.inputs.similarity_measure = options.similarity_measure
    inputnode.inputs.algorithm = options.algorithm

    outputnode = pe.Node(niu.IdentityInterface(
        fields=['transformed']),
        name='outputnode')

    transformNode = pe.Node(AtlasTransform(), name='transform')

    workflow.connect([
        (inputnode, transformNode, [('nifti', 'nifti')]),
        (inputnode, transformNode, [('atlas_name', 'atlas_name')]),
        (inputnode, transformNode, [('resolution', 'resolution')]),
        (inputnode, transformNode, [('number_of_clusters', 'number_of_clusters')]),
        (inputnode, transformNode, [('similarity_measure', 'similarity_measure')]),
        (inputnode, transformNode, [('algorithm', 'algorithm')]),
        (transformNode, outputnode, [('transformed', 'transformed')]),
    ])

    # ds_report_summary = pe.Node(
    #     DerivativesDataSink(desc='summary', keep_dtype=True),
    #     name='ds_report_summary', run_without_submitting=True,
    #     mem_gb=1)

    # summary = pe.Node(
    #     FunctionalSummary(
    #         slice_timing=run_stc,
    #         registration=('FSL', 'FreeSurfer')[freesurfer],
    #         registration_dof=bold2t1w_dof,
    #         pe_direction=metadata.get("PhaseEncodingDirection"),
    #         tr=metadata.get("RepetitionTime")),
    #     name='summary', mem_gb=DEFAULT_MEMORY_MIN_GB, run_without_submitting=True)
    # summary.inputs.dummy_scans = dummy_scans

    # workflow.connect([
    #     (summary, ds_report_summary, [('out_report', 'in_file')]),
    #     (bold_reference_wf, ds_report_validation, [
    #         ('outputnode.validation_report', 'in_file')]),
    # ])
    return workflow