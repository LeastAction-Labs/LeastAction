/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Predefined Cron Expressions for Task Scheduling
 * Format: (minute hour day month weekday)
 * Allows users to select common schedules or enter custom expressions
 */

export interface CronOption {
  value: string;
  label: string;
  description: string;
}

export const CRON_EXPRESSIONS: CronOption[] = [
  {
    value: '* * * * *',
    label: 'Every minute',
    description: 'Runs every minute of every hour',
  },
  {
    value: '*/5 * * * *',
    label: 'Every 5 minutes',
    description: 'Runs at 5-minute intervals',
  },
  {
    value: '*/30 * * * *',
    label: 'Every 30 minutes',
    description: 'Runs at 30-minute intervals',
  },
  {
    value: '0 * * * *',
    label: 'Every hour',
    description: 'Runs at the start of every hour',
  },
  {
    value: '0 0 * * *',
    label: 'Every day',
    description: 'Runs daily at midnight (00:00)',
  },
  {
    value: '0 0 * * 0',
    label: 'Every week',
    description: 'Runs every Sunday at midnight',
  },
  {
    value: '0 0 1 * *',
    label: 'Every month',
    description: 'Runs on the 1st of every month at midnight',
  },
];

/**
 * Get cron option by value
 * @param value - Cron expression string
 * @returns CronOption if found, undefined otherwise
 */
export const getCronOptionByValue = (value: string): CronOption | undefined => {
  return CRON_EXPRESSIONS.find((option) => option.value === value);
};

/**
 * Get cron description for tooltip/help text
 * @param cronExpression - Cron expression string
 * @returns Description string or the expression itself if not found
 */
export const getCronDescription = (cronExpression: string): string => {
  const option = getCronOptionByValue(cronExpression);
  return option ? option.description : 'Custom cron expression';
};
