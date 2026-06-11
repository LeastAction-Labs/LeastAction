/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef } from 'react';

import { useNavigate } from '@tanstack/react-router';

export default function NotFound() {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  const animationLoop = useCallback(() => {
    const canvas = canvasRef.current;
    const stage = stageRef.current;
    if (!canvas || !stage) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = stage.offsetWidth;
    const H = 240;
    canvas.width = W;
    canvas.height = H;

    // Stars — bright white on dark background
    const stars = Array.from({ length: 120 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 2 + 0.4,
      speed: Math.random() * 0.003 + 0.001,
      phase: Math.random() * Math.PI * 2,
    }));

    // Planet positions
    const planetCX = W - 95;
    const planetCY = 75;
    const planetR = 65;

    const earthCX = 43;
    const earthCY = 43;
    const earthR = 23;

    // Bezier control points
    const START = { x: 70, y: 50 };
    const LAND = { x: planetCX - 52, y: planetCY + 58 };
    const C1 = { x: 160, y: -30 };
    const C2 = { x: LAND.x - 80, y: LAND.y - 120 };

    function bez(
      p0: { x: number; y: number },
      p1: { x: number; y: number },
      p2: { x: number; y: number },
      p3: { x: number; y: number },
      t: number,
    ) {
      const u = 1 - t;
      return {
        x: u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
        y: u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y,
      };
    }

    function bezTan(
      p0: { x: number; y: number },
      p1: { x: number; y: number },
      p2: { x: number; y: number },
      p3: { x: number; y: number },
      t: number,
    ) {
      const u = 1 - t;
      return {
        x: 3 * (u ** 2 * (p1.x - p0.x) + 2 * u * t * (p2.x - p1.x) + t ** 2 * (p3.x - p2.x)),
        y: 3 * (u ** 2 * (p1.y - p0.y) + 2 * u * t * (p2.y - p1.y) + t ** 2 * (p3.y - p2.y)),
      };
    }

    function easeInOut(t: number) {
      return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }

    // Smoke particles
    const smokes: {
      x: number;
      y: number;
      dx: number;
      dy: number;
      life: number;
      maxLife: number;
      size: number;
    }[] = [];

    // Dust particles
    const dusts: {
      x: number;
      y: number;
      scale: number;
      life: number;
      maxLife: number;
      size: number;
    }[] = [];

    // Question marks floating
    const qmarks = [
      { x: planetCX - 25, y: planetCY - 10, size: 18, phase: 0, speed: 2.8 },
      { x: planetCX + 5, y: planetCY - 25, size: 12, phase: 1.5, speed: 3.2 },
      { x: planetCX + 18, y: planetCY + 10, size: 15, phase: 3, speed: 2.5 },
    ];

    let t = 0;
    let phase: 'travel' | 'landed' = 'travel';
    let landedTimer = 0;
    let lastTime = 0;
    const TRAVEL_DUR = 3000;
    const WAIT_DUR = 2800;
    const pathPoints: { x: number; y: number }[] = [];
    let smokeTimer = 0;
    let cancelled = false;

    function drawPlanet(
      cx: number,
      cy: number,
      r: number,
      colors: { light: string; main: string; dark: string },
      glow?: string,
    ) {
      // Outer glow
      if (glow) {
        ctx!.save();
        ctx!.shadowColor = glow;
        ctx!.shadowBlur = 40;
        ctx!.beginPath();
        ctx!.arc(cx, cy, r, 0, Math.PI * 2);
        ctx!.fillStyle = 'rgba(0,0,0,0.01)';
        ctx!.fill();
        ctx!.restore();
      }

      const grad = ctx!.createRadialGradient(cx - r * 0.25, cy - r * 0.3, 0, cx, cy, r);
      grad.addColorStop(0, colors.light);
      grad.addColorStop(0.45, colors.main);
      grad.addColorStop(1, colors.dark);
      ctx!.beginPath();
      ctx!.arc(cx, cy, r, 0, Math.PI * 2);
      ctx!.fillStyle = grad;
      ctx!.fill();

      // Shadow
      ctx!.save();
      ctx!.beginPath();
      ctx!.arc(cx, cy, r, 0, Math.PI * 2);
      ctx!.clip();
      const shadowGrad = ctx!.createRadialGradient(
        cx + r * 0.4,
        cy + r * 0.3,
        0,
        cx + r * 0.4,
        cy + r * 0.3,
        r * 1.2,
      );
      shadowGrad.addColorStop(0, 'rgba(0,0,0,0.45)');
      shadowGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx!.fillStyle = shadowGrad;
      ctx!.fillRect(cx - r, cy - r, r * 2, r * 2);
      ctx!.restore();
    }

    function drawRing(cx: number, cy: number) {
      ctx!.save();
      // Back half (behind planet)
      ctx!.beginPath();
      ctx!.ellipse(cx, cy, 90, 20, 0, 0, Math.PI * 2);
      ctx!.strokeStyle = 'rgba(230,126,34,0.22)';
      ctx!.lineWidth = 8;
      ctx!.stroke();

      // Front half (in front of planet)
      ctx!.beginPath();
      ctx!.ellipse(cx, cy, 90, 20, 0, Math.PI, Math.PI * 2);
      ctx!.strokeStyle = 'rgba(230,126,34,0.55)';
      ctx!.lineWidth = 8;
      ctx!.lineCap = 'round';
      ctx!.stroke();
      ctx!.restore();
    }

    function drawRocket(x: number, y: number, angle: number, flameOn: boolean) {
      ctx!.save();
      ctx!.translate(x, y);
      ctx!.rotate((angle * Math.PI) / 180);

      // Drop shadow / glow
      ctx!.shadowColor = 'rgba(255,140,60,0.5)';
      ctx!.shadowBlur = 8;

      // Body — silver like original
      ctx!.beginPath();
      ctx!.moveTo(0, -28);
      ctx!.bezierCurveTo(-9, -28, -13, -6, -13, 12);
      ctx!.lineTo(-13, 22);
      ctx!.lineTo(13, 22);
      ctx!.lineTo(13, 12);
      ctx!.bezierCurveTo(13, -6, 9, -28, 0, -28);
      ctx!.fillStyle = '#c8d6e5';
      ctx!.fill();
      ctx!.shadowBlur = 0;

      // Left highlight
      ctx!.beginPath();
      ctx!.moveTo(0, -28);
      ctx!.bezierCurveTo(-5, -28, -8, -6, -8, 12);
      ctx!.lineTo(-13, 12);
      ctx!.bezierCurveTo(-13, -6, -9, -28, 0, -28);
      ctx!.fillStyle = '#a0b4c8';
      ctx!.fill();

      // Right highlight
      ctx!.beginPath();
      ctx!.moveTo(0, -28);
      ctx!.bezierCurveTo(5, -28, 8, -6, 8, 12);
      ctx!.lineTo(13, 12);
      ctx!.bezierCurveTo(13, -6, 9, -28, 0, -28);
      ctx!.fillStyle = '#ddeaf5';
      ctx!.fill();

      // Window
      ctx!.beginPath();
      ctx!.arc(0, -4, 5, 0, Math.PI * 2);
      ctx!.fillStyle = '#1a3a5c';
      ctx!.fill();
      ctx!.strokeStyle = '#7aaac8';
      ctx!.lineWidth = 1.5;
      ctx!.stroke();
      // Inner window
      ctx!.beginPath();
      ctx!.arc(0, -4, 2.5, 0, Math.PI * 2);
      ctx!.fillStyle = 'rgba(42,85,128,0.7)';
      ctx!.fill();

      // Fins
      ctx!.fillStyle = '#8fa8bc';
      ctx!.beginPath();
      ctx!.moveTo(-13, 16);
      ctx!.lineTo(-19, 28);
      ctx!.lineTo(-13, 22);
      ctx!.fill();
      ctx!.beginPath();
      ctx!.moveTo(13, 16);
      ctx!.lineTo(19, 28);
      ctx!.lineTo(13, 22);
      ctx!.fill();

      // Nozzle
      ctx!.fillStyle = '#7a9bb5';
      ctx!.beginPath();
      ctx!.roundRect(-6, 22, 12, 6, 2);
      ctx!.fill();

      // Flame
      if (flameOn) {
        const flameGrad = ctx!.createRadialGradient(0, 30, 0, 0, 30, 12);
        flameGrad.addColorStop(0, 'rgba(255,245,160,0.95)');
        flameGrad.addColorStop(0.4, 'rgba(255,140,0,0.8)');
        flameGrad.addColorStop(1, 'rgba(232,69,69,0)');
        ctx!.beginPath();
        ctx!.ellipse(0, 34, 6, 12, 0, 0, Math.PI * 2);
        ctx!.fillStyle = flameGrad;
        ctx!.fill();
      }

      ctx!.restore();
    }

    function drawAlien(x: number, y: number, time: number) {
      const bobY = Math.sin(time * 0.004) * 6;
      const rot = Math.sin(time * 0.004) * 5;
      ctx!.save();
      ctx!.translate(x, y + bobY);
      ctx!.rotate((rot * Math.PI) / 180);
      ctx!.shadowColor = 'rgba(192,57,43,0.6)';
      ctx!.shadowBlur = 8;
      ctx!.font = '28px serif';
      ctx!.textAlign = 'center';
      ctx!.fillText('\u{1F47D}', 0, 0);
      ctx!.restore();
    }

    function frame(now: number) {
      if (cancelled) return;
      if (!lastTime) lastTime = now;
      const dt = now - lastTime;
      lastTime = now;

      ctx!.clearRect(0, 0, W, H);

      // Draw stars — bright white
      for (const s of stars) {
        const brightness = 0.25 + 0.55 * (0.5 + 0.5 * Math.sin(now * s.speed + s.phase));
        ctx!.beginPath();
        ctx!.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(255,255,255,${brightness})`;
        ctx!.fill();
      }

      // Draw Earth (correct planet) with glow
      drawPlanet(
        earthCX,
        earthCY,
        earthR,
        {
          light: '#3498db',
          main: '#1a5276',
          dark: '#0d2b40',
        },
        'rgba(52,152,219,0.3)',
      );
      // Earth continents
      ctx!.save();
      ctx!.beginPath();
      ctx!.arc(earthCX, earthCY, earthR, 0, Math.PI * 2);
      ctx!.clip();
      ctx!.fillStyle = 'rgba(39,174,96,0.65)';
      ctx!.beginPath();
      ctx!.ellipse(earthCX - 5, earthCY - 3, 10, 7, -0.35, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.fillStyle = 'rgba(39,174,96,0.5)';
      ctx!.beginPath();
      ctx!.ellipse(earthCX + 8, earthCY + 5, 7, 5, 0, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.restore();

      // Earth label
      ctx!.font = '9px sans-serif';
      ctx!.fillStyle = 'rgba(200,220,255,0.5)';
      ctx!.textAlign = 'left';
      ctx!.letterSpacing = '0.1em';
      ctx!.fillText('\u2190 CORRECT DESTINATION', 24, 78);

      // Draw wrong planet with glow
      drawPlanet(
        planetCX,
        planetCY,
        planetR,
        {
          light: '#e74c3c',
          main: '#c0392b',
          dark: '#922b21',
        },
        'rgba(192,57,43,0.35)',
      );

      // Planet bands
      ctx!.save();
      ctx!.beginPath();
      ctx!.arc(planetCX, planetCY, planetR, 0, Math.PI * 2);
      ctx!.clip();
      ctx!.fillStyle = 'rgba(0,0,0,0.15)';
      ctx!.fillRect(planetCX - planetR, planetCY + planetR * 0.05, planetR * 2, planetR * 0.18);
      ctx!.fillStyle = 'rgba(0,0,0,0.1)';
      ctx!.fillRect(planetCX - planetR, planetCY + planetR * 0.35, planetR * 2, planetR * 0.1);
      ctx!.restore();

      // Ring
      drawRing(planetCX, planetCY);

      // Question marks — bright on dark
      for (const q of qmarks) {
        const bobY = Math.sin(now * 0.002 * (3 / q.speed) + q.phase) * 5;
        ctx!.font = `900 ${q.size}px sans-serif`;
        ctx!.fillStyle = 'rgba(255,255,255,0.55)';
        ctx!.textAlign = 'center';
        ctx!.fillText('?', q.x, q.y + bobY);
      }

      // Dashed path — light on dark
      if (pathPoints.length > 1) {
        ctx!.save();
        ctx!.setLineDash([7, 5]);
        ctx!.strokeStyle = 'rgba(200,214,229,0.35)';
        ctx!.lineWidth = 1.8;
        ctx!.beginPath();
        ctx!.moveTo(pathPoints[0].x, pathPoints[0].y);
        for (let i = 1; i < pathPoints.length; i++) {
          ctx!.lineTo(pathPoints[i].x, pathPoints[i].y);
        }
        ctx!.stroke();
        ctx!.restore();
      }

      // Update smokes — light smoke on dark bg
      for (let i = smokes.length - 1; i >= 0; i--) {
        const s = smokes[i];
        s.life += dt;
        if (s.life >= s.maxLife) {
          smokes.splice(i, 1);
          continue;
        }
        const p = s.life / s.maxLife;
        const alpha = 0.4 * (1 - p);
        const scale = 1 + p * 1.5;
        ctx!.beginPath();
        ctx!.arc(s.x + s.dx * p, s.y + s.dy * p, (s.size * scale) / 2, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(180,200,220,${alpha})`;
        ctx!.fill();
      }

      // Update dusts
      for (let i = dusts.length - 1; i >= 0; i--) {
        const d = dusts[i];
        d.life += dt;
        if (d.life >= d.maxLife) {
          dusts.splice(i, 1);
          continue;
        }
        const p = d.life / d.maxLife;
        const alpha = 0.7 * (1 - p);
        const scale = 1 + p * 2.5;
        ctx!.beginPath();
        ctx!.arc(d.x, d.y, (d.size * scale) / 2, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(192,57,43,${alpha})`;
        ctx!.fill();
      }

      // Rocket animation
      if (phase === 'travel') {
        t = Math.min(t + dt / TRAVEL_DUR, 1);
        const e = easeInOut(t);
        const pos = bez(START, C1, C2, LAND, e);
        const tan = bezTan(START, C1, C2, LAND, e);
        const angle = (Math.atan2(tan.y, tan.x) * 180) / Math.PI + 90;

        drawRocket(pos.x, pos.y, angle, true);

        smokeTimer += dt;
        if (smokeTimer > 90) {
          smokeTimer = 0;
          smokes.push({
            x: pos.x,
            y: pos.y + 12,
            dx: (Math.random() - 0.5) * 28,
            dy: -(Math.random() * 18 + 8),
            life: 0,
            maxLife: 900,
            size: Math.random() * 8 + 5,
          });
        }

        if (pathPoints.length === 0 || t > 0) {
          pathPoints.push(pos);
        }

        if (t >= 1) {
          phase = 'landed';
          landedTimer = 0;
          for (let i = 0; i < 5; i++) {
            const angle = Math.random() * Math.PI * 2;
            const dist = Math.random() * 30 + 10;
            dusts.push({
              x: LAND.x + Math.cos(angle) * dist,
              y: LAND.y + Math.sin(angle) * dist,
              scale: 1,
              life: 0,
              maxLife: 1000,
              size: Math.random() * 16 + 8,
            });
          }
        }
      } else if (phase === 'landed') {
        landedTimer += dt;
        drawRocket(LAND.x, LAND.y, 0, false);

        if (landedTimer > 400) {
          drawAlien(LAND.x - 40, LAND.y - 10, now);
        }

        if (landedTimer >= WAIT_DUR) {
          phase = 'travel';
          t = 0;
          landedTimer = 0;
          pathPoints.length = 0;
        }
      }

      requestAnimationFrame(frame);
    }

    requestAnimationFrame(frame);

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return animationLoop();
  }, [animationLoop]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'radial-gradient(ellipse at 40% 30%, #1a0e2e 0%, #0b0e1a 50%, #050710 100%)',
        color: '#c8d6e5',
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Nebula blobs */}
      <div
        style={{
          position: 'absolute',
          width: 320,
          height: 220,
          borderRadius: '50%',
          background: 'rgba(108,52,131,0.18)',
          top: -60,
          right: -80,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 260,
          height: 180,
          borderRadius: '50%',
          background: 'rgba(192,57,43,0.12)',
          bottom: 0,
          left: -60,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      {/* Canvas animation stage */}
      <div
        ref={stageRef}
        style={{
          position: 'relative',
          width: 'min(720px, 96vw)',
          height: 240,
          marginBottom: 20,
        }}
      >
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>

      {/* Text content */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            fontSize: 'clamp(20px, 3.5vw, 32px)',
            fontWeight: 900,
            color: '#f0e0ff',
            letterSpacing: '0.04em',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            justifyContent: 'center',
          }}
        >
          404 — Wrong Planet
        </div>
        <div
          style={{
            fontSize: 'clamp(15px, 2.2vw, 21px)',
            fontWeight: 600,
            color: '#fff',
            marginTop: 8,
          }}
        >
          You've landed somewhere... unexpected
        </div>
        <div
          style={{
            fontSize: 'clamp(11px, 1.4vw, 14px)',
            fontWeight: 300,
            opacity: 0.5,
            marginTop: 6,
            letterSpacing: '0.09em',
            color: '#c8d6e5',
          }}
        >
          this isn't the page you were navigating to
        </div>
        <button
          onClick={() => void navigate({ to: '/' })}
          style={{
            marginTop: 26,
            padding: '12px 34px',
            borderRadius: 50,
            background: '#2e1f4a',
            color: '#ddd0ff',
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: '0.06em',
            border: '1px solid rgba(255,255,255,0.1)',
            cursor: 'pointer',
            boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
            transition: 'background 0.25s, transform 0.15s, box-shadow 0.25s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#3d2a63';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 8px 28px rgba(0,0,0,0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#2e1f4a';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
          }}
        >
          Return to Base
        </button>
      </div>
    </div>
  );
}
