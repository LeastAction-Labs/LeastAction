/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { Box, Button, Typography } from '@mui/material';

import type { RunActionModalDataType } from '@/contexts/ActionContext';
import { RunActionModalMode, useActionContext } from '@/contexts/ActionContext';
import { useGlobal } from '@/contexts/GlobalContext';
import { runAction } from '@/services/index';

import SessionDetailView from '../logs/SessionDetailView';
import { AutocompleteCom, BaseModal, ModalForm, QuickSearch, StyledTextField } from '../ui';

interface ActionVariablesModalProps {
  open: boolean;
  loading?: boolean;
}

export default function RunActionModal({
  open,
  loading: dataLoading = false,
}: ActionVariablesModalProps) {
  const { runActionModalData, setRunActionModalData } = useActionContext();

  const { accountLaui, projectLauis } = useGlobal();

  const [actionVariablesFormValues, setActionVariablesFormValues] = useState<Record<string, any>>(
    {},
  ); // ActionVariablesForm
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const projects =
    projectLauis.length != 0
      ? projectLauis
      : JSON.parse(localStorage.getItem('la_project_lauis') || '[]');
  // Selected values
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [selectedConnection, setSelectedConnection] = useState<string>('');
  const [selectedProject, setSelectedProject] = useState<string>(projectLauis[0]);

  // State management from second file
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionDate, setSessionDate] = useState<string>('');

  useEffect(() => {
    if (runActionModalData?.actionVariables) {
      // Initialize form values with default values from actionVariables
      const initialValues: Record<string, any> = {};
      Object.entries(runActionModalData.actionVariables).forEach(([key, value]) => {
        initialValues[key] = value;
      });
      setActionVariablesFormValues(initialValues);
    }
  }, [runActionModalData]);

  if (!runActionModalData || !setRunActionModalData) return null;

  const handleClose = () => {
    setError(null);
    setSessionId(null);
    setSessionDate('');
    setName('');
    setDescription('');
    setSelectedWorkflow('');
    setSelectedConnection('');
    setRunActionModalData({
      ...runActionModalData,
      isOpen: false,
    } as RunActionModalDataType);
  };

  const handleSubmit = async () => {
    setError(null);
    if (runActionModalData.mode === RunActionModalMode.CREATE) {
      if (!selectedProject || !selectedWorkflow || !name) {
        setError('project,workflow and name cannot be empty');
        return;
      }
    }
    setSubmitting(true);
    const preSessionId = crypto.randomUUID();
    setSessionId(preSessionId);
    setSessionDate(new Date().toISOString().split('T')[0]);
    try {
      if (runActionModalData.mode === RunActionModalMode.RUN) {
        await runAction(
          {
            item_laui: runActionModalData.actionLaui,
            action_variables: actionVariablesFormValues,
            connection_laui: selectedConnection || null,
          },
          preSessionId,
        );
      } else {
        await runAction(
          {
            ...runActionModalData.operatorData,
            name: name,
            description: description,
            parent_laui: selectedWorkflow,
            project_laui: selectedProject,
            connection_laui: selectedConnection || null,
            account_laui: accountLaui || localStorage.getItem('la_account_laui'),
            action_variables: actionVariablesFormValues,
          },
          preSessionId,
        );
      }
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  const loading = submitting || dataLoading;

  const logsActions = (
    <Button
      onClick={handleClose}
      size="small"
      variant="contained"
      sx={{
        bgcolor: 'var(--text-primary)',
        color: 'var(--bg-secondary)',
        textTransform: 'none',
        fontWeight: 'bold',
        '&:hover': {
          bgcolor: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
        },
        py: 0.5,
        px: 1.5,
      }}
    >
      Close
    </Button>
  );

  const ModalActions = sessionId ? (
    logsActions
  ) : (
    <>
      <Button
        onClick={handleClose}
        disabled={loading}
        size="small"
        variant="outlined"
        sx={{
          color: 'var(--text-secondary)',
          borderColor: 'var(--border)',
          '&:hover': {
            borderColor: 'var(--primary-main)',
            color: 'var(--text-primary)',
          },
        }}
      >
        Cancel
      </Button>
      <Button
        onClick={() => void handleSubmit()}
        disabled={loading}
        size="small"
        variant="contained"
        startIcon={<PlayArrowIcon />}
        sx={{
          bgcolor: 'var(--text-primary)',
          color: 'var(--bg-secondary)',
          textTransform: 'none',
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          },
          py: 0.5,
          px: 1.5,
          '&:disabled': {
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-disabled)',
          },
        }}
      >
        {submitting ? 'Running...' : dataLoading ? 'Loading...' : 'Run Action'}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title={sessionId ? 'Execution Logs' : 'Run Action'}
      subtitle={sessionId ? `Session: ${sessionId}` : 'Configure and execute the action'}
      actions={ModalActions}
      loading={loading && !sessionId}
      loadingText={submitting ? 'Running action...' : 'Loading data...'}
      maxWidth={sessionId ? 'md' : 'sm'}
    >
      {sessionId ? (
        <Box sx={{ height: '500px', overflow: 'hidden' }}>
          <SessionDetailView sessionId={sessionId} sessionDate={sessionDate} pollUntilStable />
        </Box>
      ) : (
        <Box sx={{ marginTop: '20px' }}>
          {runActionModalData.mode === RunActionModalMode.CREATE && (
            <>
              <StyledTextField
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                placeholder="Enter action name"
                required
                error={!!error && !name.trim()}
              />

              <StyledTextField
                label="Description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={loading}
                placeholder="Optional description"
                multiline
                rows={2}
              />
              <QuickSearch
                label="Workflow"
                value={selectedWorkflow}
                filters={{ item_type: 'folder.workflow' }}
                disabled={loading}
                onSelect={(item) => {
                  const raw = item as Record<string, unknown>;
                  const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                  setSelectedWorkflow(laui);
                }}
                placeholder="Search workflow…"
              />
              <AutocompleteCom
                label="Project"
                value={selectedProject}
                options={projects.map((p: string) => ({ value: p, label: p }))}
                onChange={(value) => setSelectedProject(value)}
                disabled={loading}
                required={true}
                fieldType="Project"
                sx={{ mb: 2 }}
              />
            </>
          )}
          <QuickSearch
            label="Connection (Optional)"
            value={selectedConnection}
            filters={{ item_type: 'connection' }}
            disabled={loading}
            onSelect={(item) => {
              const raw = item as Record<string, unknown>;
              const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
              setSelectedConnection(laui);
            }}
            placeholder="Search connection…"
          />
          <Box>
            <Typography>Action Variables</Typography>
            <ModalForm
              formValues={actionVariablesFormValues}
              setFormValues={setActionVariablesFormValues}
            />
          </Box>
        </Box>
      )}
    </BaseModal>
  );
}
