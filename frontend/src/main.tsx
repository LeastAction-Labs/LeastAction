/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createRoot } from 'react-dom/client';

import App from './App';
import './index.scss';

console.log(
  '%c⚛ LeastAction',
  'font-size:18px; font-weight:bold; color:#8b5cf6; letter-spacing:2px;',
);
console.log('%cFollowing the path of least action.');

createRoot(document.getElementById('root')!).render(<App />);
