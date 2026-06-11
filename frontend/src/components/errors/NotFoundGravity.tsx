/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

interface FallingObject {
  x: number;
  y: number;
  vy: number;
  rotation: number;
  rotationSpeed: number;
  size: number;
  opacity: number;
  type: 'cube' | 'sphere' | 'triangle' | 'document';
  landed: boolean;
  bounceCount: number;
  groundY: number;
}

interface GridDot {
  x: number;
  y: number;
  baseOpacity: number;
  pulsePhase: number;
}

export default function NotFoundGravity() {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [antiGravityDots, setAntiGravityDots] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setAntiGravityDots((d) => (d + 1) % 4);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d')!;
    if (!ctx) return;

    let W = container.offsetWidth;
    let H = container.offsetHeight;
    canvas.width = W;
    canvas.height = H;

    const GRAVITY = 0.15;
    const BOUNCE_DAMPING = 0.4;
    const GROUND_Y = H * 0.62;

    // Grid dots
    const gridSpacing = 80;
    const gridDots: GridDot[] = [];
    for (let x = gridSpacing / 2; x < W; x += gridSpacing) {
      for (let y = gridSpacing / 2; y < H; y += gridSpacing) {
        gridDots.push({
          x,
          y,
          baseOpacity: 0.12 + Math.random() * 0.08,
          pulsePhase: Math.random() * Math.PI * 2,
        });
      }
    }

    // Grid lines
    const gridLines: { x1: number; y1: number; x2: number; y2: number }[] = [];
    for (let x = gridSpacing / 2; x < W; x += gridSpacing) {
      gridLines.push({ x1: x, y1: 0, x2: x, y2: H });
    }
    for (let y = gridSpacing / 2; y < H; y += gridSpacing) {
      gridLines.push({ x1: 0, y1: y, x2: W, y2: y });
    }

    // Falling objects
    const objects: FallingObject[] = [];

    function spawnObject() {
      const types: FallingObject['type'][] = ['cube', 'sphere', 'triangle', 'document'];
      objects.push({
        x: W * 0.15 + Math.random() * W * 0.7,
        y: -40 - Math.random() * 60,
        vy: 0,
        rotation: Math.random() * 360,
        rotationSpeed: (Math.random() - 0.5) * 3,
        size: 16 + Math.random() * 20,
        opacity: 0.25 + Math.random() * 0.35,
        type: types[Math.floor(Math.random() * types.length)],
        landed: false,
        bounceCount: 0,
        groundY: GROUND_Y + Math.random() * 30,
      });
    }

    // Spawn initial objects
    for (let i = 0; i < 6; i++) {
      const obj = {
        x: W * 0.1 + Math.random() * W * 0.8,
        y: GROUND_Y + Math.random() * 20 - 10,
        vy: 0,
        rotation: Math.random() * 360,
        rotationSpeed: 0,
        size: 16 + Math.random() * 20,
        opacity: 0.15 + Math.random() * 0.2,
        type: ['cube', 'sphere', 'triangle', 'document'][
          Math.floor(Math.random() * 4)
        ] as FallingObject['type'],
        landed: true,
        bounceCount: 3,
        groundY: GROUND_Y + Math.random() * 30,
      };
      objects.push(obj);
    }

    let spawnTimer = 0;
    let cancelled = false;
    let lastTime = 0;

    // Gravity well effect center (below 404 text area)
    const wellX = W / 2;
    const wellY = GROUND_Y;

    function drawShape(obj: FallingObject, ctx: CanvasRenderingContext2D) {
      ctx.save();
      ctx.translate(obj.x, obj.y);
      ctx.rotate((obj.rotation * Math.PI) / 180);
      ctx.globalAlpha = obj.opacity;

      const s = obj.size;
      const strokeColor = `rgba(0, 0, 0, ${obj.opacity * 0.6})`;
      const fillColor = `rgba(0, 0, 0, ${obj.opacity * 0.08})`;

      switch (obj.type) {
        case 'cube':
          ctx.strokeStyle = strokeColor;
          ctx.fillStyle = fillColor;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.rect(-s / 2, -s / 2, s, s);
          ctx.fill();
          ctx.stroke();
          // Inner detail
          ctx.beginPath();
          ctx.moveTo(-s / 4, -s / 2);
          ctx.lineTo(-s / 4, s / 2);
          ctx.moveTo(-s / 2, -s / 4);
          ctx.lineTo(s / 2, -s / 4);
          ctx.strokeStyle = `rgba(0,0,0,${obj.opacity * 0.15})`;
          ctx.stroke();
          break;

        case 'sphere':
          ctx.strokeStyle = strokeColor;
          ctx.fillStyle = fillColor;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.arc(0, 0, s / 2, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          // Ellipse detail
          ctx.beginPath();
          ctx.ellipse(0, 0, s / 2, s / 5, 0, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(0,0,0,${obj.opacity * 0.2})`;
          ctx.stroke();
          break;

        case 'triangle':
          ctx.strokeStyle = strokeColor;
          ctx.fillStyle = fillColor;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(0, -s / 2);
          ctx.lineTo(s / 2, s / 2);
          ctx.lineTo(-s / 2, s / 2);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          break;

        case 'document': {
          ctx.strokeStyle = strokeColor;
          ctx.fillStyle = fillColor;
          ctx.lineWidth = 1.2;
          const w = s * 0.7;
          const h = s;
          ctx.beginPath();
          ctx.rect(-w / 2, -h / 2, w, h);
          ctx.fill();
          ctx.stroke();
          // Text lines
          ctx.strokeStyle = `rgba(0,0,0,${obj.opacity * 0.2})`;
          ctx.lineWidth = 1;
          for (let i = 0; i < 3; i++) {
            const ly = -h / 2 + h * 0.25 + i * (h * 0.2);
            ctx.beginPath();
            ctx.moveTo(-w / 2 + 3, ly);
            ctx.lineTo(w / 2 - 3 - i * 4, ly);
            ctx.stroke();
          }
          break;
        }
      }

      ctx.restore();
    }

    // Gravity distortion rings
    function drawGravityWell(ctx: CanvasRenderingContext2D, time: number) {
      ctx.save();
      // Elliptical distortion rings
      for (let i = 0; i < 3; i++) {
        const pulse = Math.sin(time * 0.001 + i * 1.2) * 0.15 + 0.85;
        const rx = (60 + i * 40) * pulse;
        const ry = (15 + i * 10) * pulse;
        const alpha = 0.08 - i * 0.02;
        ctx.beginPath();
        ctx.ellipse(wellX, wellY - 20, rx, ry, 0, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 0, 0, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      ctx.restore();
    }

    // Floating "page" being pulled down
    const floatingPage = {
      x: W / 2,
      y: H * 0.18,
      targetY: wellY - 40,
      vy: 0,
      rotation: 0,
      phase: 0, // 0=floating, 1=falling, 2=absorbed, 3=reset
      timer: 0,
      opacity: 0.6,
      size: 50,
    };

    function drawFloatingPage(ctx: CanvasRenderingContext2D, time: number) {
      const p = floatingPage;
      const wobble = Math.sin(time * 0.002) * 3;
      const floatY = p.phase === 0 ? Math.sin(time * 0.0015) * 8 : 0;

      ctx.save();
      ctx.translate(p.x, p.y + floatY);
      ctx.rotate(((p.rotation + wobble) * Math.PI) / 180);
      ctx.globalAlpha = p.opacity;

      // Page shape - folded corner
      const w = p.size * 0.7;
      const h = p.size;
      const fold = 10;

      ctx.fillStyle = `rgba(245, 242, 237, ${p.opacity})`;
      ctx.strokeStyle = `rgba(0, 0, 0, ${p.opacity * 0.3})`;
      ctx.lineWidth = 1.2;

      ctx.beginPath();
      ctx.moveTo(-w / 2, -h / 2);
      ctx.lineTo(w / 2 - fold, -h / 2);
      ctx.lineTo(w / 2, -h / 2 + fold);
      ctx.lineTo(w / 2, h / 2);
      ctx.lineTo(-w / 2, h / 2);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Fold triangle
      ctx.beginPath();
      ctx.moveTo(w / 2 - fold, -h / 2);
      ctx.lineTo(w / 2 - fold, -h / 2 + fold);
      ctx.lineTo(w / 2, -h / 2 + fold);
      ctx.strokeStyle = `rgba(0, 0, 0, ${p.opacity * 0.2})`;
      ctx.stroke();

      // Text lines on page
      ctx.strokeStyle = `rgba(0, 0, 0, ${p.opacity * 0.15})`;
      ctx.lineWidth = 1.5;
      for (let i = 0; i < 4; i++) {
        const ly = -h / 2 + 16 + i * 8;
        ctx.beginPath();
        ctx.moveTo(-w / 2 + 6, ly);
        ctx.lineTo(w / 2 - 8 - (i % 2) * 8, ly);
        ctx.stroke();
      }

      ctx.restore();
    }

    function frame(now: number) {
      if (cancelled) return;
      if (!lastTime) lastTime = now;
      const dt = Math.min(now - lastTime, 32);
      lastTime = now;

      ctx.clearRect(0, 0, W, H);

      // Background - warm off-white
      ctx.fillStyle = '#f5f2ed';
      ctx.fillRect(0, 0, W, H);

      // Grid lines
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.04)';
      ctx.lineWidth = 0.5;
      for (const line of gridLines) {
        ctx.beginPath();
        ctx.moveTo(line.x1, line.y1);
        ctx.lineTo(line.x2, line.y2);
        ctx.stroke();
      }

      // Grid dots
      for (const dot of gridDots) {
        const pulse = Math.sin(now * 0.001 + dot.pulsePhase) * 0.03;
        ctx.beginPath();
        ctx.arc(dot.x, dot.y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 0, 0, ${dot.baseOpacity + pulse})`;
        ctx.fill();
      }

      // Gravity well distortion
      drawGravityWell(ctx, now);

      // Update and draw falling objects
      spawnTimer += dt;
      if (spawnTimer > 3000 && objects.length < 20) {
        spawnTimer = 0;
        spawnObject();
      }

      for (let i = objects.length - 1; i >= 0; i--) {
        const obj = objects[i];

        if (!obj.landed) {
          obj.vy += GRAVITY;
          obj.y += obj.vy;
          obj.rotation += obj.rotationSpeed;

          // Gravity pull toward center
          const dx = wellX - obj.x;
          obj.x += dx * 0.001;

          if (obj.y >= obj.groundY) {
            obj.y = obj.groundY;
            if (obj.bounceCount < 2) {
              obj.vy = -obj.vy * BOUNCE_DAMPING;
              obj.bounceCount++;
              obj.rotationSpeed *= 0.5;
            } else {
              obj.landed = true;
              obj.vy = 0;
              obj.rotationSpeed = 0;
            }
          }
        }

        // Fade out old landed objects
        if (obj.landed) {
          obj.opacity -= 0.0001 * dt;
          if (obj.opacity <= 0) {
            objects.splice(i, 1);
            continue;
          }
        }

        drawShape(obj, ctx);
      }

      // Floating page animation
      const p = floatingPage;
      p.timer += dt;

      switch (p.phase) {
        case 0: // Floating
          if (p.timer > 2500) {
            p.phase = 1;
            p.timer = 0;
            p.vy = 0;
          }
          break;
        case 1: // Falling
          p.vy += 0.08;
          p.y += p.vy;
          p.rotation += 0.5;
          p.opacity = Math.max(0, p.opacity - 0.003);
          if (p.y >= p.targetY) {
            p.phase = 2;
            p.timer = 0;
          }
          break;
        case 2: // Absorbed - shrink and fade
          p.opacity -= 0.008;
          p.size *= 0.995;
          if (p.opacity <= 0 || p.timer > 1500) {
            p.phase = 3;
            p.timer = 0;
          }
          break;
        case 3: // Reset
          if (p.timer > 1000) {
            p.y = H * 0.18;
            p.opacity = 0;
            p.size = 50;
            p.rotation = 0;
            p.vy = 0;
            p.phase = 4;
            p.timer = 0;
          }
          break;
        case 4: // Fade in
          p.opacity = Math.min(0.6, p.opacity + 0.005);
          if (p.opacity >= 0.6) {
            p.phase = 0;
            p.timer = 0;
          }
          break;
      }

      drawFloatingPage(ctx, now);

      requestAnimationFrame(frame);
    }

    requestAnimationFrame(frame);

    const handleResize = () => {
      W = container.offsetWidth;
      H = container.offsetHeight;
      canvas.width = W;
      canvas.height = H;
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelled = true;
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        backgroundColor: '#f5f2ed',
        overflow: 'hidden',
        fontFamily: "'Georgia', 'Times New Roman', serif",
      }}
    >
      {/* Full-screen canvas for grid + animation */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      />

      {/* Top-left brand */}
      <div
        style={{
          position: 'absolute',
          top: 28,
          left: 32,
          fontSize: 18,
          fontWeight: 400,
          color: '#2a2a2a',
          letterSpacing: '0.02em',
          zIndex: 10,
          fontFamily: "'Georgia', serif",
        }}
      >
        Least Action
      </div>

      {/* Top-right icon */}
      <div
        style={{
          position: 'absolute',
          top: 24,
          right: 32,
          zIndex: 10,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            border: '1.5px solid rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            backgroundColor: 'rgba(255,255,255,0.6)',
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ color: '#2a2a2a' }}
          >
            <circle cx="8" cy="8" r="3" />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => {
              const rad = (angle * Math.PI) / 180;
              return (
                <line
                  key={angle}
                  x1={8 + Math.cos(rad) * 5}
                  y1={8 + Math.sin(rad) * 5}
                  x2={8 + Math.cos(rad) * 7}
                  y2={8 + Math.sin(rad) * 7}
                />
              );
            })}
          </svg>
        </div>
      </div>

      {/* Center content */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          zIndex: 10,
          pointerEvents: 'none',
        }}
      >
        {/* 404 number */}
        <div
          style={{
            fontSize: 'clamp(100px, 18vw, 200px)',
            fontWeight: 400,
            color: '#1a1a1a',
            lineHeight: 1,
            fontFamily: "'Georgia', 'Times New Roman', serif",
            letterSpacing: '-0.02em',
          }}
        >
          404
        </div>

        {/* Gravity Error subtitle */}
        <div
          style={{
            fontSize: 'clamp(18px, 3vw, 28px)',
            fontStyle: 'italic',
            color: '#3a3a3a',
            marginTop: 4,
            fontWeight: 400,
            letterSpacing: '0.01em',
          }}
        >
          Gravity Error
        </div>

        {/* Divider */}
        <div
          style={{
            width: 40,
            height: 1.5,
            backgroundColor: 'rgba(0,0,0,0.15)',
            margin: '16px auto',
          }}
        />

        {/* Description */}
        <div
          style={{
            fontSize: 'clamp(12px, 1.8vw, 16px)',
            color: '#666',
            fontFamily: "'Courier New', monospace",
            lineHeight: 1.6,
            fontWeight: 400,
          }}
        >
          Gravity pulled this page
          <br />
          into another dimension.
        </div>

        {/* Working on anti-gravity */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            marginTop: 16,
            fontSize: 'clamp(10px, 1.2vw, 12px)',
            color: '#999',
            fontFamily: "'Courier New', monospace",
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              backgroundColor: '#bbb',
              display: 'inline-block',
            }}
          />
          WORKING ON ANTI-GRAVITY{'.'.repeat(antiGravityDots)}
        </div>

        {/* Buttons */}
        <div
          style={{
            display: 'flex',
            gap: 16,
            justifyContent: 'center',
            marginTop: 32,
            pointerEvents: 'auto',
          }}
        >
          <button
            onClick={() => void navigate({ to: '/' })}
            style={{
              padding: '10px 28px',
              fontSize: 14,
              fontFamily: "'Courier New', monospace",
              letterSpacing: '0.05em',
              color: '#2a2a2a',
              backgroundColor: 'transparent',
              border: '1.5px solid rgba(0,0,0,0.2)',
              borderRadius: 4,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.04)';
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.35)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.2)';
            }}
          >
            <span style={{ fontSize: 12 }}>&uarr;</span> Go Home
          </button>
          <button
            onClick={() => window.history.back()}
            style={{
              padding: '10px 28px',
              fontSize: 14,
              fontFamily: "'Courier New', monospace",
              letterSpacing: '0.05em',
              color: '#2a2a2a',
              backgroundColor: 'transparent',
              border: '1.5px solid rgba(0,0,0,0.2)',
              borderRadius: 4,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.04)';
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.35)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.2)';
            }}
          >
            <span style={{ fontSize: 12 }}>&larr;</span> Go Back
          </button>
        </div>
      </div>

      {/* Bottom-left error code */}
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          left: 32,
          fontSize: 11,
          color: '#aaa',
          fontFamily: "'Courier New', monospace",
          letterSpacing: '0.08em',
          zIndex: 10,
        }}
      >
        ERR_GRAVITY_404
      </div>

      {/* Bottom-right version */}
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          right: 32,
          fontSize: 11,
          color: '#aaa',
          fontFamily: "'Courier New', monospace",
          letterSpacing: '0.08em',
          zIndex: 10,
        }}
      >
        v4.0.4
      </div>
    </div>
  );
}
