/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Add as AddIcon, Delete as DeleteIcon, Lock as LockIcon } from '@mui/icons-material';
import { Autocomplete, Box, Button, Chip, IconButton, TextField, Typography } from '@mui/material';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import dayjs from 'dayjs';

import {
  createArrayTemplate,
  getDataType,
  getItemTypeFromKey as getItemTypeFromFieldName,
  isLauiKey as isLauiField,
  isLockedValue,
} from '@/components/browse/FieldRenderer/FancyJsonEditor/fieldDetection';
import { FONT_SIZES } from '@/constants';
import { CRON_EXPRESSIONS, getCronDescription } from '@/constants/cronExpressions';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { getTimeZoneLabel } from '@/utils/timeFormat';

import { QuickSearch } from '../QuickSearch';

interface ModalFormProps {
  formValues: Record<string, any>;
  setFormValues: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}

export const ModalForm = ({ formValues, setFormValues }: ModalFormProps) => {
  const { timeZone } = useTimeFormat();
  const tzLabel = timeZone === 'utc' ? 'UTC' : getTimeZoneLabel();

  const handleInputChange = (key: string, value: any) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleArrayAdd = (key: string) => {
    const currentArray = formValues[key] || [];
    let newItem = '';

    // If there's already an item, use it as a template
    if (currentArray.length > 0) {
      const lastItem = currentArray[currentArray.length - 1];
      newItem = createArrayTemplate(lastItem);
    }

    setFormValues((prev) => ({
      ...prev,
      [key]: [...currentArray, newItem],
    }));
  };

  const handleArrayRemove = (key: string, index: number) => {
    const currentArray = [...(formValues[key] || [])];
    currentArray.splice(index, 1);
    setFormValues((prev) => ({
      ...prev,
      [key]: currentArray,
    }));
  };

  const handleArrayItemChange = (key: string, index: number, value: any) => {
    const currentArray = [...(formValues[key] || [])];
    currentArray[index] = value;
    setFormValues((prev) => ({
      ...prev,
      [key]: currentArray,
    }));
  };

  const handleObjectChange = (key: string, objectKey: string, value: any) => {
    const currentObject = { ...(formValues[key] || {}) };
    currentObject[objectKey] = value;
    setFormValues((prev) => ({
      ...prev,
      [key]: currentObject,
    }));
  };

  const renderString = (
    key: string,
    value: string,
    onChange: (value: any) => void,
    isLocked: boolean = false,
  ) => {
    const showAsLaui = isLauiField(key, value);

    const isDateField = (key === 'start_date' || key === 'end_date') && !showAsLaui;
    const isFrequencyField = key === 'frequency' && !showAsLaui;

    return (
      <Box
        sx={{
          mb: 2,
          p: 2,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: isLocked ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
          opacity: isLocked ? 0.7 : 1,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 1.5,
          }}
        >
          <Typography
            sx={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            {key}
          </Typography>
          <Chip
            label="String"
            size="small"
            sx={{
              ml: 1.5,
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
            }}
          />
          {isLocked && !showAsLaui && (
            <LockIcon
              sx={{
                ml: 1,
                fontSize: '16px',
                color: 'var(--text-secondary)',
              }}
            />
          )}
        </Box>
        {showAsLaui ? (
          <QuickSearch
            label={key}
            value={value}
            filters={{ item_type: getItemTypeFromFieldName(key) }}
            disabled={isLocked}
            disambigField={getItemTypeFromFieldName(key) === 'task' ? 'partition' : undefined}
            onSelect={(rawItem) => {
              if (!isLocked) {
                const raw = rawItem as Record<string, unknown>;
                const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                onChange(laui);
              }
            }}
            placeholder={`Search ${getItemTypeFromFieldName(key)}…`}
          />
        ) : isDateField ? (
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DateTimePicker
              label={`${key} (${tzLabel})`}
              value={value ? dayjs(value.replace(/Z$/, '')) : null}
              onChange={(newValue) =>
                !isLocked && onChange(newValue ? newValue.format('YYYY-MM-DDTHH:mm:ss.SSS[Z]') : '')
              }
              disabled={isLocked}
              ampm={false}
              slotProps={{
                textField: {
                  fullWidth: true,
                  size: 'small',
                  sx: {
                    '& .MuiOutlinedInput-root': {
                      fontSize: '14px',
                      backgroundColor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      '&:hover .MuiOutlinedInput-notchedOutline': {
                        borderColor: 'var(--accent)',
                      },
                      '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                        borderColor: 'var(--accent)',
                      },
                      '&.Mui-disabled': {
                        backgroundColor: 'var(--bg-tertiary)',
                      },
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: '14px',
                      color: 'var(--text-secondary)',
                      '&.Mui-focused': { color: 'var(--accent)' },
                      '&.Mui-disabled': { color: 'var(--text-disabled)' },
                    },
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'var(--border)',
                    },
                    '& .MuiInputBase-input': {
                      color: 'var(--text-primary)',
                      WebkitTextFillColor: 'var(--text-primary)',
                    },
                    '& .MuiPickersSectionList-sectionContent, & .MuiPickersSectionList-sectionSeparator':
                      {
                        color: 'var(--text-primary)',
                      },
                    '& .MuiIconButton-root': {
                      color: 'var(--text-secondary)',
                    },
                  },
                },
              }}
            />
          </LocalizationProvider>
        ) : isFrequencyField ? (
          <Autocomplete
            freeSolo
            options={CRON_EXPRESSIONS.map((opt) => opt.value)}
            value={value || ''}
            onChange={(_, newValue) => !isLocked && onChange(newValue || '')}
            onInputChange={(_, newInputValue) => !isLocked && onChange(newInputValue)}
            disabled={isLocked}
            isOptionEqualToValue={(option, val) => option === val}
            renderOption={(props, option) => {
              const cronOption = CRON_EXPRESSIONS.find((c) => c.value === option);
              return (
                <Box
                  component="li"
                  {...props}
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start !important',
                    py: 1,
                    px: 1.5,
                    '&:hover': { bgcolor: 'var(--bg-tertiary) !important' },
                    '&.Mui-focused': {
                      bgcolor: 'var(--bg-tertiary) !important',
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      width: '100%',
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.BASE,
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {cronOption?.label || option}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        color: 'var(--accent)',
                        fontFamily: 'monospace',
                        bgcolor: 'var(--bg-primary)',
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {option}
                    </Typography>
                  </Box>
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      color: 'var(--text-secondary)',
                      textAlign: 'left',
                    }}
                  >
                    {cronOption?.description || 'Custom expression'}
                  </Typography>
                </Box>
              );
            }}
            slotProps={{
              popper: { sx: { zIndex: 1400 } },
              paper: {
                sx: {
                  bgcolor: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  '& .MuiAutocomplete-listbox': { p: 0.5 },
                  '& .MuiAutocomplete-option': { borderRadius: 'var(--radius-sm)', mb: 0.25 },
                  '& .MuiAutocomplete-noOptions': {
                    color: 'var(--text-secondary)',
                    fontSize: '12px',
                  },
                },
              },
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Frequency (Cron Expression)"
                placeholder="e.g., * * * * * or select from list"
                helperText={
                  value
                    ? getCronDescription(value)
                    : 'Select from preset options or enter custom cron expression (format: minute hour day month weekday)'
                }
                sx={{
                  '& .MuiInputBase-root': {
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--accent)',
                  },
                  '& .MuiInputBase-root.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--accent)',
                  },
                  '& .MuiInputBase-root.Mui-disabled': {
                    backgroundColor: 'var(--bg-tertiary)',
                  },
                  '& .MuiInputLabel-root.Mui-disabled': {
                    color: 'var(--text-secondary)',
                  },
                  '& .Mui-disabled .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                  '& .MuiFormHelperText-root': {
                    color: 'var(--text-secondary)',
                    fontSize: '11px',
                  },
                }}
              />
            )}
          />
        ) : (
          <TextField
            fullWidth
            size="small"
            value={value}
            onChange={(e) => !isLocked && onChange(e.target.value)}
            disabled={isLocked}
            multiline={value?.length > 50}
            rows={value?.length > 50 ? 3 : 1}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'var(--bg-primary)',
                '& fieldset': {
                  borderColor: 'var(--border)',
                },
                '&:hover fieldset': {
                  borderColor: isLocked ? 'var(--border)' : 'var(--text-secondary)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'var(--primary-main)',
                },
                '&.Mui-disabled': {
                  bgcolor: 'var(--bg-tertiary)',
                },
              },
              '& .MuiInputBase-input': {
                color: 'var(--text-primary)',
                fontSize: '14px',
              },
            }}
          />
        )}
      </Box>
    );
  };

  const renderNumber = (
    key: string,
    value: number,
    onChange: (value: any) => void,
    isLocked: boolean = false,
  ) => {
    return (
      <Box
        sx={{
          mb: 2,
          p: 2,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: isLocked ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
          opacity: isLocked ? 0.7 : 1,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 1.5,
          }}
        >
          <Typography
            sx={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            {key}
          </Typography>
          <Chip
            label="Number"
            size="small"
            sx={{
              ml: 1.5,
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
            }}
          />
          {isLocked && (
            <LockIcon
              sx={{
                ml: 1,
                fontSize: '16px',
                color: 'var(--text-secondary)',
              }}
            />
          )}
        </Box>
        <TextField
          fullWidth
          size="small"
          type="number"
          value={value}
          onChange={(e) => !isLocked && onChange(parseFloat(e.target.value) || 0)}
          disabled={isLocked}
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: 'var(--bg-primary)',
              '& fieldset': {
                borderColor: 'var(--border)',
              },
              '&:hover fieldset': {
                borderColor: isLocked ? 'var(--border)' : 'var(--text-secondary)',
              },
              '&.Mui-focused fieldset': {
                borderColor: 'var(--primary-main)',
              },
              '&.Mui-disabled': {
                bgcolor: 'var(--bg-tertiary)',
              },
            },
            '& .MuiInputBase-input': {
              color: 'var(--text-primary)',
              fontSize: '14px',
            },
          }}
        />
      </Box>
    );
  };

  const renderBoolean = (
    key: string,
    value: boolean,
    onChange: (value: any) => void,
    isLocked: boolean = false,
  ) => {
    return (
      <Box
        sx={{
          mb: 2,
          p: 2,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: isLocked ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
          opacity: isLocked ? 0.7 : 1,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 1.5,
          }}
        >
          <Typography
            sx={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            {key}
          </Typography>
          <Chip
            label="Boolean"
            size="small"
            sx={{
              ml: 1.5,
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
            }}
          />
          {isLocked && (
            <LockIcon
              sx={{
                ml: 1,
                fontSize: '16px',
                color: 'var(--text-secondary)',
              }}
            />
          )}
        </Box>
        <Box
          sx={{
            display: 'flex',
            gap: 1.5,
          }}
        >
          <Button
            variant={value === true ? 'contained' : 'outlined'}
            size="small"
            onClick={() => !isLocked && onChange(true)}
            disabled={isLocked}
            sx={{
              textTransform: 'none',
              borderColor: 'var(--border)',
              color: value === true ? 'var(--bg-secondary)' : 'var(--text-secondary)',
              bgcolor: value === true ? 'var(--text-primary)' : 'transparent',
              '&:hover': {
                borderColor: isLocked ? 'var(--border)' : 'var(--primary-main)',
                bgcolor: value === true ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
                color: value === true ? 'var(--text-primary)' : 'var(--text-primary)',
              },
              '&.Mui-disabled': {
                opacity: 0.5,
              },
            }}
          >
            True
          </Button>
          <Button
            variant={value === false ? 'contained' : 'outlined'}
            size="small"
            onClick={() => !isLocked && onChange(false)}
            disabled={isLocked}
            sx={{
              textTransform: 'none',
              borderColor: 'var(--border)',
              color: value === false ? 'var(--bg-secondary)' : 'var(--text-secondary)',
              bgcolor: value === false ? 'var(--text-primary)' : 'transparent',
              '&:hover': {
                borderColor: isLocked ? 'var(--border)' : 'var(--primary-main)',
                bgcolor: value === false ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
                color: value === false ? 'var(--text-primary)' : 'var(--text-primary)',
              },
              '&.Mui-disabled': {
                opacity: 0.5,
              },
            }}
          >
            False
          </Button>
        </Box>
      </Box>
    );
  };

  const renderArray = (key: string, value: any[], _onChange: (value: any) => void) => {
    const renderArrayItem = (item: any, index: number) => {
      const itemType = getDataType(item);
      const locked = isLockedValue(item);

      if (itemType === 'string' && isLauiField(key, item)) {
        return (
          <QuickSearch
            label={key}
            value={item as string}
            filters={{ item_type: getItemTypeFromFieldName(key) }}
            disabled={locked}
            disambigField={getItemTypeFromFieldName(key) === 'task' ? 'partition' : undefined}
            onSelect={(rawItem) => {
              if (!locked) {
                const raw = rawItem as Record<string, unknown>;
                const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                handleArrayItemChange(key, index, laui);
              }
            }}
            placeholder={`Search ${getItemTypeFromFieldName(key)}…`}
          />
        );
      } else if (itemType === 'object') {
        return (
          <Box
            sx={{
              p: 2,
              border: '1px solid var(--border)',
              borderRadius: 1,
              bgcolor: 'var(--bg-primary)',
              width: '100%',
            }}
          >
            {Object.entries(item || {}).map(([objKey, objValue]) => {
              const objValueType = getDataType(objValue);
              const objLocked = isLockedValue(objValue);

              if (objValueType === 'string' && isLauiField(objKey, objValue)) {
                return (
                  <Box key={objKey} sx={{ mt: 2, '&:last-child': { mb: 0 } }}>
                    <QuickSearch
                      label={objKey}
                      value={objValue as string}
                      filters={{
                        item_type: getItemTypeFromFieldName(objKey),
                      }}
                      disabled={objLocked}
                      disambigField={
                        getItemTypeFromFieldName(objKey) === 'task' ? 'partition' : undefined
                      }
                      onSelect={(rawItem) => {
                        if (!objLocked) {
                          const raw = rawItem as Record<string, unknown>;
                          const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                          const newItem = { ...item, [objKey]: laui };
                          handleArrayItemChange(key, index, newItem);
                        }
                      }}
                      placeholder={`Search ${getItemTypeFromFieldName(objKey)}…`}
                    />
                  </Box>
                );
              } else {
                return (
                  <Box key={objKey} sx={{ position: 'relative', marginTop: 2 }}>
                    {objLocked && (
                      <LockIcon
                        sx={{
                          position: 'absolute',
                          right: 8,
                          top: 12,
                          fontSize: '16px',
                          color: 'var(--text-secondary)',
                          zIndex: 1,
                        }}
                      />
                    )}
                    <TextField
                      fullWidth
                      size="small"
                      label={objKey}
                      value={objValue as string}
                      onChange={(e) => {
                        if (!objLocked) {
                          const newItem = {
                            ...item,
                            [objKey]: e.target.value,
                          };
                          handleArrayItemChange(key, index, newItem);
                        }
                      }}
                      disabled={objLocked}
                      sx={{
                        mb: 3,
                        '&:last-child': { mb: 0 },
                        '& .MuiOutlinedInput-root': {
                          bgcolor: objLocked ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                          '& fieldset': {
                            borderColor: 'var(--border)',
                          },
                          '&:hover fieldset': {
                            borderColor: objLocked ? 'var(--border)' : 'var(--text-secondary)',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: 'var(--primary-main)',
                          },
                          '&.Mui-disabled': {
                            bgcolor: 'var(--bg-tertiary)',
                          },
                        },
                        '& .MuiInputBase-input': {
                          color: 'var(--text-primary)',
                          fontSize: '14px',
                        },
                        '& .MuiInputLabel-root': {
                          color: 'var(--text-secondary)',
                          fontSize: '14px',
                        },
                      }}
                    />
                  </Box>
                );
              }
            })}
          </Box>
        );
      } else {
        return (
          <Box sx={{ position: 'relative', width: '100%' }}>
            {locked && (
              <LockIcon
                sx={{
                  position: 'absolute',
                  right: 8,
                  top: 8,
                  fontSize: '16px',
                  color: 'var(--text-secondary)',
                  zIndex: 1,
                }}
              />
            )}
            <TextField
              fullWidth
              size="small"
              value={item}
              onChange={(e) => !locked && handleArrayItemChange(key, index, e.target.value)}
              disabled={locked}
              placeholder={`Item ${index + 1}`}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: locked ? 'var(--bg-tertiary)' : 'var(--bg-primary)',
                  '& fieldset': {
                    borderColor: 'var(--border)',
                  },
                  '&:hover fieldset': {
                    borderColor: locked ? 'var(--border)' : 'var(--text-secondary)',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: 'var(--primary-main)',
                  },
                  '&.Mui-disabled': {
                    bgcolor: 'var(--bg-tertiary)',
                  },
                },
                '& .MuiInputBase-input': {
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                },
              }}
            />
          </Box>
        );
      }
    };

    return (
      <Box
        sx={{
          mb: 4,
          p: 2.5,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 3,
          }}
        >
          <Typography
            sx={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            {key}
          </Typography>
          <Chip
            label="Array"
            size="small"
            sx={{
              ml: 1.5,
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
            }}
          />
          <IconButton
            size="small"
            onClick={() => handleArrayAdd(key)}
            sx={{
              ml: 1.5,
              color: 'var(--text-secondary)',
              '&:hover': {
                color: 'var(--primary-main)',
                bgcolor: 'var(--bg-tertiary)',
              },
            }}
          >
            <AddIcon fontSize="small" />
          </IconButton>
        </Box>
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
          }}
        >
          {(value || []).map((item: any, index: number) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                gap: 1.5,
                alignItems: 'flex-start',
              }}
            >
              <Box sx={{ flex: 1 }}>{renderArrayItem(item, index)}</Box>
              <IconButton
                size="small"
                onClick={() => handleArrayRemove(key, index)}
                sx={{
                  mt: 0.5,
                  color: 'var(--text-secondary)',
                  '&:hover': {
                    color: 'var(--error-main)',
                    bgcolor: 'var(--bg-tertiary)',
                  },
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
          {(!value || value.length === 0) && (
            <Typography
              sx={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                fontStyle: 'italic',
                py: 1,
              }}
            >
              No items. Click + to add.
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  const renderObject = (
    key: string,
    obj: object,
    _onChange: (value: any) => void,
  ): React.ReactElement => {
    return (
      <Box
        sx={{
          mb: 2,
          p: 2,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 1.5,
          }}
        >
          <Typography
            sx={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            {key}
          </Typography>
          <Chip
            label="Object"
            size="small"
            sx={{
              ml: 1.5,
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              fontSize: '11px',
            }}
          />
        </Box>
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 1.5,
          }}
        >
          {Object.entries(obj || {}).map(([objKey, objValue]) => {
            const valueType = getDataType(objValue);
            const locked = isLockedValue(objValue);

            if (valueType === 'object') {
              return (
                <Box key={objKey}>
                  {renderObject(objKey, objValue as object, (newValue) =>
                    handleObjectChange(key, objKey, newValue),
                  )}
                </Box>
              );
            } else if (valueType === 'array') {
              return (
                <Box key={objKey}>
                  {renderArray(objKey, objValue as any[], (newValue) =>
                    handleObjectChange(key, objKey, newValue),
                  )}
                </Box>
              );
            } else if (valueType === 'string') {
              if (isLauiField(objKey, objValue)) {
                return (
                  <Box key={objKey}>
                    <Typography
                      sx={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        mb: 1,
                      }}
                    >
                      {objKey}
                    </Typography>
                    <QuickSearch
                      label={objKey}
                      value={objValue as string}
                      filters={{
                        item_type: getItemTypeFromFieldName(objKey),
                      }}
                      disabled={locked}
                      disambigField={
                        getItemTypeFromFieldName(objKey) === 'task' ? 'partition' : undefined
                      }
                      onSelect={(rawItem) => {
                        if (!locked) {
                          const raw = rawItem as Record<string, unknown>;
                          const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                          handleObjectChange(key, objKey, laui);
                        }
                      }}
                      placeholder={`Search ${getItemTypeFromFieldName(objKey)}…`}
                    />
                  </Box>
                );
              } else {
                return (
                  <Box key={objKey} sx={{ position: 'relative' }}>
                    {locked && (
                      <LockIcon
                        sx={{
                          position: 'absolute',
                          right: 8,
                          top: 12,
                          fontSize: '16px',
                          color: 'var(--text-secondary)',
                          zIndex: 1,
                        }}
                      />
                    )}
                    <TextField
                      fullWidth
                      size="small"
                      label={objKey}
                      value={objValue as string}
                      onChange={(e) => !locked && handleObjectChange(key, objKey, e.target.value)}
                      disabled={locked}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          bgcolor: locked ? 'var(--bg-tertiary)' : 'var(--bg-primary)',
                          '& fieldset': {
                            borderColor: 'var(--border)',
                          },
                          '&:hover fieldset': {
                            borderColor: locked ? 'var(--border)' : 'var(--text-secondary)',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: 'var(--primary-main)',
                          },
                          '&.Mui-disabled': {
                            bgcolor: 'var(--bg-tertiary)',
                          },
                        },
                        '& .MuiInputBase-input': {
                          color: 'var(--text-primary)',
                          fontSize: '14px',
                        },
                        '& .MuiInputLabel-root': {
                          color: 'var(--text-secondary)',
                          fontSize: '14px',
                        },
                      }}
                    />
                  </Box>
                );
              }
            } else if (valueType === 'number') {
              return (
                <Box key={objKey} sx={{ position: 'relative' }}>
                  {locked && (
                    <LockIcon
                      sx={{
                        position: 'absolute',
                        right: 8,
                        top: 12,
                        fontSize: '16px',
                        color: 'var(--text-secondary)',
                        zIndex: 1,
                      }}
                    />
                  )}
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label={objKey}
                    value={objValue as number}
                    onChange={(e) =>
                      !locked && handleObjectChange(key, objKey, parseFloat(e.target.value) || 0)
                    }
                    disabled={locked}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        bgcolor: locked ? 'var(--bg-tertiary)' : 'var(--bg-primary)',
                        '& fieldset': {
                          borderColor: 'var(--border)',
                        },
                        '&:hover fieldset': {
                          borderColor: locked ? 'var(--border)' : 'var(--text-secondary)',
                        },
                        '&.Mui-focused fieldset': {
                          borderColor: 'var(--primary-main)',
                        },
                        '&.Mui-disabled': {
                          bgcolor: 'var(--bg-tertiary)',
                        },
                      },
                      '& .MuiInputBase-input': {
                        color: 'var(--text-primary)',
                        fontSize: '14px',
                      },
                      '& .MuiInputLabel-root': {
                        color: 'var(--text-secondary)',
                        fontSize: '14px',
                      },
                    }}
                  />
                </Box>
              );
            } else if (valueType === 'boolean') {
              return (
                <Box key={objKey} sx={{ mb: 0 }}>
                  <Typography
                    sx={{
                      fontSize: '12px',
                      color: 'var(--text-secondary)',
                      mb: 1,
                    }}
                  >
                    {objKey}
                    {locked && (
                      <LockIcon
                        sx={{
                          ml: 1,
                          fontSize: '14px',
                          verticalAlign: 'middle',
                        }}
                      />
                    )}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1.5 }}>
                    <Button
                      variant={objValue === true ? 'contained' : 'outlined'}
                      size="small"
                      onClick={() => !locked && handleObjectChange(key, objKey, true)}
                      disabled={locked}
                      sx={{
                        textTransform: 'none',
                        borderColor: 'var(--border)',
                        color: objValue === true ? 'var(--bg-secondary)' : 'var(--text-secondary)',
                        bgcolor: objValue === true ? 'var(--text-primary)' : 'transparent',
                        '&:hover': {
                          borderColor: locked ? 'var(--border)' : 'var(--primary-main)',
                          bgcolor: objValue === true ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
                          color: 'var(--text-primary)',
                        },
                        '&.Mui-disabled': {
                          opacity: 0.5,
                        },
                      }}
                    >
                      True
                    </Button>
                    <Button
                      variant={objValue === false ? 'contained' : 'outlined'}
                      size="small"
                      onClick={() => !locked && handleObjectChange(key, objKey, false)}
                      disabled={locked}
                      sx={{
                        textTransform: 'none',
                        borderColor: 'var(--border)',
                        color: objValue === false ? 'var(--bg-secondary)' : 'var(--text-secondary)',
                        bgcolor: objValue === false ? 'var(--text-primary)' : 'transparent',
                        '&:hover': {
                          borderColor: locked ? 'var(--border)' : 'var(--primary-main)',
                          bgcolor:
                            objValue === false ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
                          color: 'var(--text-primary)',
                        },
                        '&.Mui-disabled': {
                          opacity: 0.5,
                        },
                      }}
                    >
                      False
                    </Button>
                  </Box>
                </Box>
              );
            }
            return null;
          })}
          {(!obj || Object.keys(obj).length === 0) && (
            <Typography
              sx={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                fontStyle: 'italic',
                py: 1,
              }}
            >
              Empty object
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  // Main render function that delegates to appropriate renderer
  const renderValue = (key: string, value: any): React.ReactElement | null => {
    const dataType = getDataType(value);
    const currentValue = formValues[key] !== undefined ? formValues[key] : value;
    const locked = isLockedValue(currentValue);

    switch (dataType) {
      case 'string':
        return renderString(
          key,
          currentValue,
          (newValue) => handleInputChange(key, newValue),
          locked,
        );

      case 'number':
        return renderNumber(
          key,
          currentValue,
          (newValue) => handleInputChange(key, newValue),
          locked,
        );

      case 'boolean':
        return renderBoolean(
          key,
          currentValue,
          (newValue) => handleInputChange(key, newValue),
          locked,
        );

      case 'array':
        return renderArray(key, currentValue, (newValue) => handleInputChange(key, newValue));

      case 'object':
        return renderObject(key, currentValue, (newValue) => handleInputChange(key, newValue));

      default:
        // Treat null or unknown types as empty strings
        return renderString(key, '', (newValue) => handleInputChange(key, newValue));
    }
  };

  return (
    <Box sx={{ p: 0 }}>
      {Object.entries(formValues).map(([key, value]) => (
        <Box key={key}>{renderValue(key, value)}</Box>
      ))}
    </Box>
  );
};
