/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute, redirect } from '@tanstack/react-router';

// Redirect bare "/" based on view mode preference.
// Business users go to /explore; developers go to /path.
export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const mode = localStorage.getItem('la_view_mode');
    // eslint-disable-next-line @typescript-eslint/only-throw-error
    throw redirect({ to: mode === 'business' ? '/explore' : '/path', search: {} });
  },
  component: () => null,
});
