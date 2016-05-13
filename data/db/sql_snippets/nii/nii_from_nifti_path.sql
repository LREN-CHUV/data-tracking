SELECT 
participant.id,participant.birthdate,participant.gender,participant.handedness,scan.date,session.value,sequence_type.name,repetition.value,nifti.path 

FROM mri.nifti nifti 
LEFT JOIN (mri.repetition repetition, mri.sequence_type sequence_type, mri.sequence sequence, mri.session session, mri.scan scan, mri.participant participant) 
ON (nifti.repetition_id=repetition.id AND sequence.sequence_type_id=sequence_type.id AND repetition.sequence_id=sequence.id AND sequence.session_id=session.id AND session.scan_id=scan.id AND scan.participant_id=participant.id) 

WHERE nifti.path='/home/mirco/Workspace/GitLab/mri/nifti-meta/test/data/PR00165/01/al_B1mapping_v2d/02/B1map_sPR00165-0002-00001-000001-01.nii'

ORDER BY participant.id,participant.birthdate,scan.date, session.value, sequence_type.name, repetition.value, nifti.path;