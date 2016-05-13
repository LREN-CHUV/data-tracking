SELECT 
participant.id,participant.birthdate,participant.gender,participant.handedness,scan.date,session.value,sequence_type.name,repetition.value,nifti.path 

FROM mri.nifti nifti 
LEFT JOIN (mri.repetition repetition, mri.sequence_type sequence_type, mri.sequence sequence, mri.session session, mri.scan scan, mri.participant participant) 
ON (nifti.repetition_id=repetition.id AND sequence.sequence_type_id=sequence_type.id AND repetition.sequence_id=sequence.id AND sequence.session_id=session.id AND session.scan_id=scan.id AND scan.participant_id=participant.id) 

WHERE participant.id='5ERqqoco'

ORDER BY participant.id,participant.birthdate,scan.date, session.value, sequence_type.name, repetition.value, nifti.path;