/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useRef } from 'react';

/**
 * Renders arbitrary HTML inside a sandboxed iframe so its styles and scripts
 * cannot leak into the app. Scripts run isolated (no same-origin access).
 */
export default function IframeContent({
  content,
  height,
}: {
  content: string;
  height?: string | number;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  return (
    <iframe
      ref={iframeRef}
      title="HTML content"
      srcDoc={content}
      sandbox="allow-scripts"
      style={{
        width: '100%',
        minHeight: height ?? 300,
        height: height ?? undefined,
        border: 'none',
        display: 'block',
        background: '#fff',
      }}
      onLoad={() => {
        const iframe = iframeRef.current;
        if (iframe?.contentDocument?.body && !height) {
          iframe.style.height = iframe.contentDocument.body.scrollHeight + 'px';
        }
      }}
    />
  );
}
