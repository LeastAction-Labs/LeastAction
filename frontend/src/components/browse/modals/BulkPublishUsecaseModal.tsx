/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import {
  Cancel,
  CheckCircle,
  SaveAlt as CreateIcon,
  CloudUpload as PublishIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';

import { parsePayloadMeta } from '@/components/marketplace/UsecaseImportModal/usecaseParser';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { FONT_SIZES } from '@/constants';
import { useNotification } from '@/contexts/NotificationContext';
import {
  createCatalogItem,
  getCatalogItemById,
  searchCatalogItems,
} from '@/services/catalog.service';
import { publishItem } from '@/services/marketplace.service';

interface PayloadValidation {
  laui: string;
  name: string;
  content: string;
  valid: boolean;
  errors: string[];
  operatorName?: string;
  connectionName?: string;
}

interface BulkPublishUsecaseModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  selectedLauis: string[];
  sourceType?: 'payload' | 'skill';
  parentLaui?: string;
  projectLaui?: string;
  accountLaui?: string;
  mode?: 'create' | 'create_and_publish';
}

const PAYLOAD_STEPS_CREATE = ['Name & Description', 'Validate Payloads'];
const SKILL_STEPS_CREATE = ['Name & Description', 'Review Skills'];
const PAYLOAD_STEPS_PUBLISH = ['Name & Description', 'Validate Payloads', 'Metadata & Publish'];
const SKILL_STEPS_PUBLISH = ['Name & Description', 'Review Skills', 'Metadata & Publish'];

export default function BulkPublishUsecaseModal({
  open,
  onClose,
  onSuccess,
  selectedLauis,
  sourceType = 'payload',
  parentLaui,
  projectLaui,
  accountLaui,
  mode = 'create',
}: BulkPublishUsecaseModalProps) {
  const isSkillSource = sourceType === 'skill';
  const willPublish = mode === 'create_and_publish';
  const { showSuccess } = useNotification();

  // Step state
  const [activeStep, setActiveStep] = useState(0);

  // Step A: Name form
  const [usecaseName, setUsecaseName] = useState('');
  const [usecaseDescription, setUsecaseDescription] = useState('');
  const [nameError, setNameError] = useState('');

  // Step B: Validation
  const [payloads, setPayloads] = useState<PayloadValidation[]>([]);
  const [loading, setLoading] = useState(false);

  // Step C: Metadata + Publish
  const [tags, setTags] = useState('');
  const [category, setCategory] = useState('');
  const [publisher, setPublisher] = useState('');
  const [isPublishing, setIsPublishing] = useState(false);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setActiveStep(0);
      setUsecaseName('');
      setUsecaseDescription('');
      setNameError('');
      setPayloads([]);
      setLoading(false);
      setTags('');
      setCategory('');
      setPublisher('');
      setIsPublishing(false);
    }
  }, [open]);

  const validateName = (name: string): string => {
    if (!name.trim()) return 'Name is required';
    const finalName = name.endsWith('.usecase') ? name : `${name}.usecase`;
    const base = finalName.replace(/\.usecase$/, '');
    if (!/^[a-zA-Z0-9_-]+$/.test(base))
      return 'Name can only contain letters, numbers, hyphens, and underscores';
    return '';
  };

  const getFinalName = () => {
    const n = usecaseName.trim();
    return n.endsWith('.usecase') ? n : `${n}.usecase`;
  };

  const handleNext = async () => {
    if (activeStep === 0) {
      const err = validateName(usecaseName);
      if (err) {
        setNameError(err);
        return;
      }
      // Check if usecase with same name already exists locally
      const finalName = getFinalName();
      try {
        const localResult = await searchCatalogItems('usecase', false, {
          filters: { name: finalName },
          perPage: 1,
          projection: ['name'],
        });
        if (localResult?.items?.length > 0) {
          setNameError(`A usecase named "${finalName}" already exists`);
          return;
        }
      } catch (e: any) {
        console.warn('Failed to check local catalog for duplicates:', e.message);
      }
      // Also check marketplace when publishing
      if (willPublish) {
        try {
          const result = await searchCatalogItems('usecase', true, {
            filters: { name: finalName },
            perPage: 1,
            projection: ['name'],
          });
          if (result?.items?.length > 0) {
            setNameError(`A usecase named "${finalName}" already exists in the marketplace`);
            return;
          }
        } catch (e: any) {
          console.warn('Failed to check marketplace for duplicates:', e.message);
        }
      }
      setNameError('');
      setActiveStep(1);
      await fetchAndValidate();
    } else if (activeStep === 1) {
      if (willPublish) {
        setActiveStep(2);
      } else {
        await handleCreate();
      }
    }
  };

  const fetchAndValidate = async () => {
    setLoading(true);
    try {
      const results = await Promise.all(
        selectedLauis.map(async (laui) => {
          const item = await getCatalogItemById(laui);
          if (isSkillSource) {
            // For skills: no metadata validation needed, store full item JSON as content
            return {
              laui,
              name: item.name,
              content: JSON.stringify(item),
              valid: true,
              errors: [] as string[],
              operatorName: undefined,
              connectionName: undefined,
            };
          }
          const content = (item.content as string) || '';
          const { meta } = parsePayloadMeta(content);
          const errors: string[] = [];
          if (!meta) {
            errors.push('No valid metadata comment block found');
          } else {
            if (!meta.operator_name) errors.push('Missing operator_name');
            if (!meta.connection_name) errors.push('Missing connection_name');
          }
          return {
            laui,
            name: item.name,
            content,
            valid: errors.length === 0,
            errors,
            operatorName: meta?.operator_name,
            connectionName: meta?.connection_name,
          };
        }),
      );
      setPayloads(results);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  const allValid = payloads.length > 0 && payloads.every((p) => p.valid);

  const buildUsecaseData = () => {
    const bundledItems = payloads.map((p) =>
      JSON.stringify({ filename: p.name, content: p.content }),
    );
    const usecaseData: Record<string, any> = {
      item_type: 'usecase',
      name: getFinalName(),
      description: usecaseDescription || undefined,
      payloads: isSkillSource ? [] : bundledItems,
      ...(isSkillSource ? { skills: bundledItems } : {}),
      ...(projectLaui ? { project_laui: projectLaui } : {}),
      ...(accountLaui ? { account_laui: accountLaui } : {}),
    };
    return usecaseData;
  };

  const handleCreate = async () => {
    setIsPublishing(true);
    try {
      const usecaseData = buildUsecaseData();
      if (!parentLaui) {
        return;
      }
      await createCatalogItem({ ...usecaseData, parent_laui: parentLaui });
      showSuccess(`Usecase "${getFinalName()}" created`);
      onSuccess?.();
      onClose();
    } catch {
      /* ignore */
    } finally {
      setIsPublishing(false);
    }
  };

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      const usecaseData = buildUsecaseData();

      const tagArray = tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      // For skills, ensure "skills" tag is always present
      if (isSkillSource) {
        const hasSkillTag = tagArray.some(
          (t) => t.toLowerCase() === 'skill' || t.toLowerCase() === 'skills',
        );
        if (!hasSkillTag) tagArray.unshift('skills');
      }

      if (tagArray.length > 0) usecaseData.tags = tagArray;
      if (category.trim()) usecaseData.category = category.trim();
      if (publisher.trim()) usecaseData.publisher = publisher.trim();

      await publishItem(usecaseData);

      // Also save usecase to local catalog so it appears in the sidebar
      if (parentLaui) {
        try {
          await createCatalogItem({ ...usecaseData, parent_laui: parentLaui });
        } catch (localErr: any) {
          console.warn('Failed to save usecase locally:', localErr.message);
        }
      }

      showSuccess(`Usecase "${getFinalName()}" published to marketplace`);
      onSuccess?.();
      onClose();
    } catch {
      /* ignore */
    } finally {
      setIsPublishing(false);
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
              {willPublish
                ? `Publishing ${selectedLauis.length} ${isSkillSource ? 'skill(s)' : 'payload(s)'} as a usecase to the marketplace.`
                : `Creating a usecase from ${selectedLauis.length} ${isSkillSource ? 'skill(s)' : 'payload(s)'}.`}
            </Typography>
            <TextField
              label="Usecase Name"
              value={usecaseName}
              onChange={(e) => {
                setUsecaseName(e.target.value);
                if (nameError) setNameError('');
              }}
              error={!!nameError}
              helperText={nameError || 'Will auto-append ".usecase" if missing'}
              size="small"
              fullWidth
              autoFocus
              sx={textFieldSx}
            />
            <TextField
              label="Description"
              value={usecaseDescription}
              onChange={(e) => setUsecaseDescription(e.target.value)}
              size="small"
              fullWidth
              multiline
              rows={3}
              sx={textFieldSx}
            />
          </Box>
        );

      case 1:
        return (
          <Box sx={{ mt: 1 }}>
            {loading ? (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <LinearProgress sx={{ mb: 2 }} />
                <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
                  {isSkillSource ? 'Fetching skills...' : 'Validating payloads...'}
                </Typography>
              </Box>
            ) : isSkillSource ? (
              <>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.SM,
                    color: 'var(--text-secondary)',
                    mb: 1,
                  }}
                >
                  The following skills will be bundled into the usecase.
                </Typography>
                <List dense>
                  {payloads.map((p) => (
                    <ListItem key={p.laui} sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <CheckCircle sx={{ color: '#4caf50', fontSize: 20 }} />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography
                            sx={{
                              fontSize: FONT_SIZES.SM,
                              color: 'var(--text-primary)',
                            }}
                          >
                            {p.name}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            ) : (
              <>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.SM,
                    color: 'var(--text-secondary)',
                    mb: 1,
                  }}
                >
                  Each payload must have a metadata comment block with operator_name and
                  connection_name.
                </Typography>
                <List dense>
                  {payloads.map((p) => (
                    <ListItem key={p.laui} sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {p.valid ? (
                          <CheckCircle sx={{ color: '#4caf50', fontSize: 20 }} />
                        ) : (
                          <Cancel sx={{ color: '#f44336', fontSize: 20 }} />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 1,
                            }}
                          >
                            <Typography
                              sx={{
                                fontSize: FONT_SIZES.SM,
                                color: 'var(--text-primary)',
                              }}
                            >
                              {p.name}
                            </Typography>
                            {p.operatorName && (
                              <Chip label={p.operatorName} size="small" sx={chipSx} />
                            )}
                            {p.connectionName && (
                              <Chip label={p.connectionName} size="small" sx={chipSx} />
                            )}
                          </Box>
                        }
                        secondary={
                          p.errors.length > 0 ? (
                            <Typography
                              sx={{
                                fontSize: FONT_SIZES.XS,
                                color: '#f44336',
                              }}
                            >
                              {p.errors.join(', ')}
                            </Typography>
                          ) : null
                        }
                      />
                    </ListItem>
                  ))}
                </List>
                {!allValid && (
                  <Typography sx={{ fontSize: FONT_SIZES.SM, color: '#f44336', mt: 1 }}>
                    Fix invalid payloads before publishing. Each payload must have a metadata header
                    with operator_name and connection_name.
                  </Typography>
                )}
              </>
            )}
          </Box>
        );

      case 2:
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
              {`Publishing "${getFinalName()}" with ${payloads.length} ${isSkillSource ? 'skill(s)' : 'payload(s)'} to marketplace. ${isSkillSource ? 'The "skills" tag will be added automatically.' : 'Optional metadata:'}`}
            </Typography>
            <TextField
              label={isSkillSource ? 'Additional Tags (comma-separated)' : 'Tags (comma-separated)'}
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              size="small"
              fullWidth
              placeholder={
                isSkillSource
                  ? 'e.g. nlp, classification ("skills" tag auto-added)'
                  : 'e.g. python, sql, etl'
              }
              helperText={
                isSkillSource
                  ? 'The "skills" tag is compulsory and will be included automatically'
                  : undefined
              }
              sx={textFieldSx}
            />
            <TextField
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              size="small"
              fullWidth
              placeholder="e.g. Data, AI, DevOps"
              sx={textFieldSx}
            />
            <TextField
              label="Publisher"
              value={publisher}
              onChange={(e) => setPublisher(e.target.value)}
              size="small"
              fullWidth
              placeholder="e.g. LeastAction"
              sx={textFieldSx}
            />
          </Box>
        );

      default:
        return null;
    }
  };

  const getActions = () => {
    const cancelBtn = (
      <Button
        onClick={onClose}
        disabled={isPublishing}
        size="small"
        variant="outlined"
        sx={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}
      >
        Cancel
      </Button>
    );

    if (activeStep === 0) {
      return (
        <>
          {cancelBtn}
          <Button
            onClick={() => void handleNext()}
            size="small"
            variant="contained"
            disabled={!usecaseName.trim()}
            sx={{ bgcolor: 'var(--text-primary)', color: 'var(--bg-primary)' }}
          >
            Next
          </Button>
        </>
      );
    }

    if (activeStep === 1) {
      return (
        <>
          {cancelBtn}
          <Button
            onClick={() => setActiveStep(0)}
            size="small"
            variant="outlined"
            sx={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}
          >
            Back
          </Button>
          <Button
            onClick={() => void handleNext()}
            size="small"
            variant="contained"
            disabled={loading || !allValid || isPublishing}
            startIcon={!willPublish ? <CreateIcon /> : undefined}
            sx={
              willPublish
                ? { bgcolor: 'var(--text-primary)', color: 'var(--bg-primary)' }
                : {
                    bgcolor: '#4caf50',
                    color: '#fff',
                    '&:hover': { bgcolor: '#388e3c' },
                  }
            }
          >
            {!willPublish ? (isPublishing ? 'Creating...' : 'Create Usecase') : 'Next'}
          </Button>
        </>
      );
    }

    return (
      <>
        {cancelBtn}
        <Button
          onClick={() => setActiveStep(1)}
          size="small"
          variant="outlined"
          disabled={isPublishing}
          sx={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}
        >
          Back
        </Button>
        <Button
          onClick={() => void handlePublish()}
          size="small"
          variant="contained"
          disabled={isPublishing}
          startIcon={<PublishIcon />}
          sx={{
            bgcolor: '#4caf50',
            color: '#fff',
            '&:hover': { bgcolor: '#388e3c' },
          }}
        >
          {isPublishing ? 'Publishing...' : 'Create & Publish'}
        </Button>
      </>
    );
  };

  return (
    <BaseModal
      open={open}
      onClose={isPublishing ? () => {} : onClose}
      title={willPublish ? 'Create & Publish Usecase' : 'Create Usecase'}
      subtitle={`${selectedLauis.length} ${isSkillSource ? 'skill(s)' : 'payload(s)'} selected`}
      maxWidth="sm"
      actions={getActions()}
    >
      <Stepper
        activeStep={activeStep}
        sx={{
          mb: 2,
          '& .MuiStepLabel-label': {
            color: 'var(--text-secondary)',
            fontSize: FONT_SIZES.SM,
          },
        }}
      >
        {(willPublish
          ? isSkillSource
            ? SKILL_STEPS_PUBLISH
            : PAYLOAD_STEPS_PUBLISH
          : isSkillSource
            ? SKILL_STEPS_CREATE
            : PAYLOAD_STEPS_CREATE
        ).map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {renderStepContent()}
    </BaseModal>
  );
}

const textFieldSx = {
  '& .MuiInputBase-root': {
    color: 'var(--text-primary)',
    bgcolor: 'var(--bg-secondary)',
  },
  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
  '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border)' },
};

const chipSx = {
  fontSize: '0.7rem',
  height: 20,
  bgcolor: 'var(--bg-secondary)',
  color: 'var(--text-secondary)',
  borderColor: 'var(--border)',
  border: '1px solid',
};
