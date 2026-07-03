/**
 * das-overlay.js — Custom SVG execution marker overlay for lightweight-charts.
 *
 * Ports the marker overlay previously inlined in index.html (CONCEPT_GLYPHS,
 * findBarAt, renderCustomMarkers, click handler) into a reusable factory so
 * any lightweight-charts container can render DAS-style triangle/diamond
 * execution markers.
 *
 * Usage:
 *   const overlay = createDasOverlay({
 *     containerEl: document.getElementById('chart-host'), // position:relative
 *     chart,                          // LWC chart instance
 *     candleSeries,                   // candlestick / line series
 *     shape: 'T1',                    // 'T1' | 'T7' | 'D1' | 'D6' (default 'T1')
 *     priceLines: [{price,color,title,lineStyle}],  // optional dashed horizontals
 *     getTrades: () => [trade],       // called on every render — allows live updates
 *     onMarkerClick: (execution, trade, domEvent) => { ... },
 *     sizePct: 6,                     // marker height as % of visible price range
 *   });
 *   overlay.setTrades([...]);
 *   overlay.destroy();
 *
 * Trade shape (caller-supplied):
 *   {
 *     id: 'unique',
 *     direction: 'long' | 'short',
 *     entryTime:  unix-seconds | 'YYYY-MM-DD',
 *     entryPrice: number,
 *     exitTime:   unix-seconds | 'YYYY-MM-DD',
 *     exitPrice:  number,
 *   }
 *
 * The factory is intentionally self-contained: it appends its own
 * `.das-overlay` <div> to containerEl, owns all listener subscriptions,
 * and is destroyed via .destroy(). Multiple overlays on one page are
 * supported (each instance is independent).
 */
(function () {
  'use strict';

  // ── Glyph builders ─────────────────────────────────────────────────────────
  // Verbatim port of CONCEPT_GLYPHS from index.html. Polygon points are
  // 18×18 SVG viewBox units; the wrapping <svg> handles final pixel sizing.
  // Buy = bright cyan-blue (#00bfff), Sell = bright red (#ff4444). White stroke
  // keeps triangles legible against any background color (blue-gray cards or
  // black/white candle bodies).
  const CONCEPT_GLYPHS = {
    T1: (isBuy) => {
      const c = isBuy ? '#00bfff' : '#ff4444';
      const points = isBuy ? '9,1 17,16 1,16' : '1,1 17,1 9,16';
      return `<polygon points="${points}" fill="${c}" stroke="#ffffff" stroke-width="1.5"/>`;
    },
    T7: (isBuy) => {
      const c = isBuy ? '#00bfff' : '#ff4444';
      const points = isBuy ? '9,1 17,16 1,16' : '1,1 17,1 9,16';
      return `<polygon points="${points}" fill="none" stroke="${c}" stroke-width="3" stroke-linejoin="round"/><polygon points="${points}" fill="${c}" stroke="#ffffff" stroke-width="1.5"/>`;
    },
    D1: (isBuy) => {
      const c = isBuy ? '#00bfff' : '#ff4444';
      return `<polygon points="9,1 17,9 9,17 1,9" fill="${c}" stroke="#ffffff" stroke-width="1.5"/>`;
    },
    D6: (isBuy) => {
      const c = isBuy ? '#00bfff' : '#ff4444';
      return `<polygon points="9,1 17,9 9,17 1,9" fill="none" stroke="${c}" stroke-width="3" stroke-linejoin="round"/><polygon points="9,1 17,9 9,17 1,9" fill="${c}" stroke="#ffffff" stroke-width="1.5"/>`;
    },
  };

  function svg(inner, w, h) {
    return `<svg viewBox="0 0 18 18" width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
  }

  function isConceptShape(s) {
    return s === 'T1' || s === 'T7' || s === 'D1' || s === 'D6';
  }

  // ── Bar snapping helpers ───────────────────────────────────────────────────
  // Verbatim port from index.html. Critical: intraday executions are
  // Unix-second timestamps and may not match loaded candle.time exactly.
  function dateKey(value) {
    if (typeof value === 'number') {
      return new Date(value * 1000).toISOString().slice(0, 10);
    }
    return String(value).slice(0, 10);
  }

  function findBarAt(bars, time) {
    if (!bars || !bars.length) return null;
    if (typeof bars[0].time === 'number' && typeof time === 'number') {
      if (time < bars[0].time) return null;
      for (let i = 0; i < bars.length; i += 1) {
        const current = bars[i];
        const next = bars[i + 1];
        if (current.time === time) return current;
        if (current.time <= time && (!next || time < next.time)) return current;
      }
      return null;
    }
    const target = dateKey(time);
    const first = dateKey(bars[0].time);
    const last = dateKey(bars[bars.length - 1].time);
    if (target < first || target > last) return null;
    let prior = null;
    for (const bar of bars) {
      const key = dateKey(bar.time);
      if (key === target) return bar;
      if (key < target) prior = bar;
      if (key > target) break;
    }
    return prior;
  }

  // ── Factory ────────────────────────────────────────────────────────────────
  /**
   * @param {Object} opts
   * @param {HTMLElement} opts.containerEl  Parent div (position:relative). The
   *   overlay creates its own child div appended to this element.
   * @param {Object} opts.chart  Lightweight-charts chart instance.
   * @param {Object} opts.candleSeries  The price series to snap executions to.
   * @param {string} [opts.shape='T1']  Concept glyph: T1 | T7 | D1 | D6.
   * @param {Array} [opts.priceLines]  Optional horizontal price lines drawn on
   *   candleSeries via createPriceLine. Each: {price, color, title, lineStyle}.
   * @param {Function} [opts.getTrades]  Returns array of trades for render.
   *   Re-invoked on every redraw so the caller can supply live data without
   *   explicitly calling setTrades().
   * @param {Function} [opts.onMarkerClick]  Callback (execution, trade, evt)
   *   where execution = {id, type:'entry'|'exit', side:'buy'|'sell', time, price}.
   * @param {number} [opts.sizePct=6]  Marker height as % of visible price range.
   */
  window.createDasOverlay = function createDasOverlay(opts) {
    if (!opts || !opts.containerEl || !opts.chart || !opts.candleSeries) {
      throw new Error('createDasOverlay: containerEl, chart, and candleSeries are required');
    }

    const containerEl = opts.containerEl;
    const chart = opts.chart;
    const candleSeries = opts.candleSeries;
    const shape = isConceptShape(opts.shape) ? opts.shape : 'T1';
    let sizePct = Math.max(0.1, Math.min(50, Number(opts.sizePct) || 6));
    const onMarkerClick = typeof opts.onMarkerClick === 'function' ? opts.onMarkerClick : null;
    const priceLines = Array.isArray(opts.priceLines) ? opts.priceLines : [];
    // Optional dynamic size function — called on every render. Lets the
    // caller tie marker size to a live input (e.g. #marker-size) without
    // rebuilding the overlay.
    const getSizePct = typeof opts.getSizePct === 'function' ? opts.getSizePct : null;

    // Ensure the container is a positioning context so the absolute overlay
    // stacks inside it rather than the page.
    const cs = window.getComputedStyle(containerEl);
    if (cs.position === 'static') {
      containerEl.style.position = 'relative';
    }

    // Create overlay element. Inline base styles mirror index.html's
    // #marker-overlay: inset 0, pointer-events: none container, but children
    // pointer-events: auto so markers are clickable.
    const overlayEl = document.createElement('div');
    overlayEl.className = 'das-overlay';
    overlayEl.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:5;overflow:hidden;';
    // Force layout so subsequent clientWidth/clientHeight are non-zero.
    containerEl.appendChild(overlayEl);

    // Per-marker child styles. We use inline class so consumers don't have to
    // load any CSS. Triangle aspect matches index.html exactly (1.15).
    const TRIANGLE_ASPECT = 1.15;

    // State
    let selectedTradeId = null;
    let pendingRender = false;
    let tradesOverride = null; // set by setTrades()
    let customPriceLineRefs = [];
    let destroyed = false;

    function getTrades() {
      if (tradesOverride) return tradesOverride;
      if (typeof opts.getTrades === 'function') return opts.getTrades() || [];
      return [];
    }

    function drawCustomPriceLines(trades) {
      // Remove any previously drawn lines
      customPriceLineRefs.forEach((ref) => {
        try { candleSeries.removePriceLine(ref); } catch (_) {}
      });
      customPriceLineRefs = [];
      if (!priceLines.length || typeof candleSeries.createPriceLine !== 'function') return;
      const styleEnum = (window.LightweightCharts && window.LightweightCharts.LineStyle) || {};
      for (const pl of priceLines) {
        if (pl == null || typeof pl.price !== 'number') continue;
        const lineOpts = {
          price: pl.price,
          color: pl.color || '#888',
          lineWidth: pl.lineWidth || 1,
          axisLabelVisible: pl.axisLabelVisible !== false,
          title: pl.title || '',
        };
        if (pl.lineStyle != null) lineOpts.lineStyle = pl.lineStyle;
        else if (styleEnum.Dashed != null) lineOpts.lineStyle = styleEnum.Dashed;
        try {
          customPriceLineRefs.push(candleSeries.createPriceLine(lineOpts));
        } catch (_) { /* ignore */ }
      }
    }

    function measureBarWidthFrom(bars, bar) {
      if (!bars || !bars.length || !bar) return 0;
      const idx = bars.findIndex((b) => b && b.time === bar.time);
      const next = idx >= 0 ? bars[idx + 1] : null;
      const prev = idx > 0 ? bars[idx - 1] : null;
      const x = chart.timeScale().timeToCoordinate(bar.time);
      if (x == null) return 0;
      if (next) {
        const nx = chart.timeScale().timeToCoordinate(next.time);
        if (nx != null) return Math.abs(nx - x);
      }
      if (prev) {
        const px = chart.timeScale().timeToCoordinate(prev.time);
        if (px != null) return Math.abs(x - px);
      }
      return 0;
    }

    function render() {
      if (destroyed) return;
      if (!chart || !candleSeries) return;

      const trades = getTrades();
      drawCustomPriceLines(trades);

      if (!isConceptShape(shape)) {
        overlayEl.innerHTML = '';
        return;
      }

      const glyphFn = CONCEPT_GLYPHS[shape];

      // Compute on-screen price pixel density so marker size stays proportional
      // to the price range, not the chart canvas height. Two known y's from
      // priceToCoordinate give us the price span in pixels.
      let pricePerPixel = 0;
      let priceSpan = 0;
      try {
        const priceScale = candleSeries.priceScale();
        const visibleRange = priceScale && priceScale.getVisibleRange ? priceScale.getVisibleRange() : null;
        if (visibleRange && visibleRange.from != null && visibleRange.to != null) {
          priceSpan = Math.abs(visibleRange.to - visibleRange.from);
          const yMin = candleSeries.priceToCoordinate(Math.min(visibleRange.from, visibleRange.to));
          const yMax = candleSeries.priceToCoordinate(Math.max(visibleRange.from, visibleRange.to));
          if (yMin != null && yMax != null) {
            const px = Math.abs(yMax - yMin);
            if (px > 0) pricePerPixel = priceSpan / px;
          }
        }
      } catch (_) { /* price scale not ready */ }

      // Marker height as % of visible price range. Either fixed (sizePct at
      // construction) or live (getSizePct callback wired to a slider/input).
      const liveSizePct = getSizePct ? Number(getSizePct()) : null;
      const effectiveSizePct = liveSizePct != null && Number.isFinite(liveSizePct)
        ? Math.max(0.1, Math.min(50, liveSizePct))
        : sizePct;
      const markerPriceH = priceSpan > 0 ? priceSpan * (effectiveSizePct / 100) : 0.6;
      const markerPxH = pricePerPixel > 0 ? markerPriceH / pricePerPixel : 18;
      const isTriangle = shape === 'T1' || shape === 'T7';
      const markerPxW = isTriangle ? markerPxH * TRIANGLE_ASPECT : markerPxH;

      const chartWidth = overlayEl.clientWidth || containerEl.clientWidth || 0;
      const chartHeight = overlayEl.clientHeight || containerEl.clientHeight || 0;

      const html = [];
      for (const trade of trades) {
        if (!trade || !trade.id) continue;
        // ORB trades don't carry bars; orb.html sets bars via getTrades so
        // findBarAt uses the trade's own bars property if present, else the
        // chart has none so we fall back to coordinate-time.
        const bars = Array.isArray(trade.bars) ? trade.bars : null;

        const entrySide = trade.direction === 'long' ? 'buy' : 'sell';
        const exitSide = trade.direction === 'long' ? 'sell' : 'buy';

        const items = [
          {
            side: entrySide,
            time: trade.entryTime,
            barTime: trade.entryBarTime || trade.entryTime,
            anchor: trade.entryAnchor || 'bar_start',
            price: trade.entryPrice,
            type: 'entry',
          },
          { side: exitSide, time: trade.exitTime, barTime: trade.exitBarTime || trade.exitTime, anchor: trade.exitAnchor || 'bar_start', price: trade.exitPrice, type: 'exit' },
        ];

        for (const m of items) {
          if (m.time == null || m.price == null) continue;

          let x = null;
          if (bars) {
            const bar = findBarAt(bars, m.barTime || m.time);
            if (!bar) continue;
            x = chart.timeScale().timeToCoordinate(bar.time);
            if (x != null && m.anchor === 'bar_close') {
              x += measureBarWidthFrom(bars, bar);
            }
          } else {
            // No bars provided — try direct coordinate. LWC accepts both
            // numeric and YYYY-MM-DD times for timeToCoordinate.
            x = chart.timeScale().timeToCoordinate(m.time);
          }
          if (x == null) continue;

          // Y stays on the actual execution price; never snap to candle center.
          const y = candleSeries.priceToCoordinate(m.price);
          if (y == null) continue;

          // Prune off-viewport markers so absolute children don't expand the
          // page when the user pans hard left/right.
          const pad = Math.max(markerPxW, markerPxH);
          if (x < -pad || x > chartWidth + pad || y < -pad || y > chartHeight + pad) continue;

          const isBuy = m.side === 'buy';
          const sel = trade.id === selectedTradeId;
          const inner = glyphFn(isBuy);
          const w = markerPxW.toFixed(2);
          const h = markerPxH.toFixed(2);
          const style = `position:absolute;transform:translate(-50%,-50%);pointer-events:auto;cursor:pointer;line-height:0;left:${x.toFixed(2)}px;top:${y.toFixed(2)}px;width:${w}px;height:${h}px;${sel ? 'filter:drop-shadow(0 0 3px rgba(255,255,255,0.85));' : ''}`;
          html.push(
            `<div data-trade-id="${escapeAttr(trade.id)}" data-marker-type="${m.type}" data-marker-side="${m.side}" data-trade-direction="${trade.direction}" style="${style}">${svg(inner, w, h)}</div>`
          );
        }
      }
      overlayEl.innerHTML = html.join('');
    }

    function escapeAttr(s) {
      return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function scheduleRender() {
      if (destroyed || pendingRender) return;
      pendingRender = true;
      requestAnimationFrame(() => {
        pendingRender = false;
        render();
      });
    }

    // Click delegation on the overlay root. Only fires for descendants
    // marked with [data-trade-id] since pointer-events: none is inherited.
    function onClick(e) {
      const el = e.target.closest && e.target.closest('[data-trade-id]');
      if (!el) return;
      const tradeId = el.dataset.tradeId;
      const markerType = el.dataset.markerType;
      const markerSide = el.dataset.markerSide;
      const tradeDirection = el.dataset.tradeDirection;
      selectedTradeId = tradeId;
      scheduleRender();
      if (onMarkerClick) {
        const trade = getTrades().find((t) => t && t.id === tradeId) || { id: tradeId };
        const execution = {
          id: tradeId,
          type: markerType,                 // 'entry' | 'exit'
          side: markerSide,                 // 'buy' | 'sell'
          direction: tradeDirection,       // 'long' | 'short'
          time: markerType === 'entry' ? trade.entryTime : trade.exitTime,
          price: markerType === 'entry' ? trade.entryPrice : trade.exitPrice,
          trade,
          domEvent: e,
          // Helper: anchor pixel coords for popup positioning.
          getAnchorPx: () => {
            const rect = el.getBoundingClientRect();
            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
          },
        };
        try {
          onMarkerClick(execution, trade, e);
        } catch (err) {
          // Don't let caller errors break the overlay.
          // eslint-disable-next-line no-console
          console.error('[das-overlay] onMarkerClick threw:', err);
        }
      }
    }

    overlayEl.addEventListener('click', onClick);

    // Subscriptions to chart events drive re-renders. While dragging the price
    // axis, LWC mutates the price→pixel transform every frame without firing
    // a resize or visible-range event — we track pointer/wheel gestures on
    // containerEl and keep rendering for a few extra frames after release.
    const timeScale = chart.timeScale();
    let visibleRangeHandler = null;
    if (typeof timeScale.subscribeVisibleTimeRangeChange === 'function') {
      visibleRangeHandler = () => scheduleRender();
      timeScale.subscribeVisibleTimeRangeChange(visibleRangeHandler);
    }
    let logicalRangeHandler = null;
    if (typeof timeScale.subscribeVisibleLogicalRangeChange === 'function') {
      logicalRangeHandler = () => scheduleRender();
      timeScale.subscribeVisibleLogicalRangeChange(logicalRangeHandler);
    }
    let priceSizeHandler = null;
    try {
      const rightScale = chart.priceScale && chart.priceScale('right');
      if (rightScale && typeof rightScale.subscribeSizeChange === 'function') {
        priceSizeHandler = () => scheduleRender();
        rightScale.subscribeSizeChange(priceSizeHandler);
      }
    } catch (_) { /* ignore */ }

    // ResizeObserver — covers container resizes (responsive layout, fullscreen).
    let resizeObserver = null;
    if (typeof ResizeObserver === 'function') {
      resizeObserver = new ResizeObserver(() => scheduleRender());
      resizeObserver.observe(containerEl);
    }

    // Pointer / wheel tracking. While dragging, keep re-rendering for ~30
    // frames so markers stay glued to candle coordinates during price-axis
    // gestures that don't emit events.
    let trackingFrames = 0;
    let trackingRaf = 0;
    let pointerDown = false;
    function startTracking(frames) {
      trackingFrames = Math.max(trackingFrames, frames);
      if (trackingRaf) return;
      const tick = () => {
        scheduleRender();
        if (pointerDown || trackingFrames > 0) {
          trackingFrames = Math.max(0, trackingFrames - 1);
          trackingRaf = requestAnimationFrame(tick);
        } else {
          trackingRaf = 0;
        }
      };
      trackingRaf = requestAnimationFrame(tick);
    }
    function onPointerDown() { pointerDown = true; startTracking(30); }
    function onPointerUp() { pointerDown = false; startTracking(20); }
    function onPointerCancel() { pointerDown = false; startTracking(20); }
    function onWheel() { startTracking(30); }
    function onDblClick() { startTracking(30); }
    function onBlur() { pointerDown = false; startTracking(20); }

    containerEl.addEventListener('pointerdown', onPointerDown, { passive: true });
    window.addEventListener('pointerup', onPointerUp, { passive: true });
    window.addEventListener('pointercancel', onPointerCancel, { passive: true });
    window.addEventListener('blur', onBlur);
    containerEl.addEventListener('wheel', onWheel, { passive: true });
    containerEl.addEventListener('dblclick', onDblClick);

    // Window resize handler as a ResizeObserver fallback (older browsers).
    function onWindowResize() { scheduleRender(); }
    window.addEventListener('resize', onWindowResize);

    // ── Initial paint ────────────────────────────────────────────────────────
    // Defer one frame so the chart has measured its container.
    requestAnimationFrame(render);

    // ── Public API ──────────────────────────────────────────────────────────
    return {
      /**
       * Imperatively set trades. Subsequent redraws will use these instead of
       * getTrades() until cleared with setTrades(null).
       */
      setTrades(trades) {
        tradesOverride = Array.isArray(trades) ? trades : null;
        scheduleRender();
      },
      /** Trigger an immediate redraw. Useful after external data changes. */
      refresh() { scheduleRender(); },
      /** Currently selected trade id (or null). */
      getSelectedId() { return selectedTradeId; },
      setSelectedId(id) { selectedTradeId = id; scheduleRender(); },
      /** Override sizePct at runtime. Ignored if getSizePct was provided. */
      setSizePct(v) {
        if (typeof v === 'number' && Number.isFinite(v)) {
          sizePct = Math.max(0.1, Math.min(50, v));
          scheduleRender();
        }
      },
      /** Current shape. Changing requires destroy+recreate (not supported here). */
      getShape() { return shape; },
      /** The overlay DOM element. */
      getElement() { return overlayEl; },
      /** Tear down all DOM + listeners. Safe to call multiple times. */
      destroy() {
        if (destroyed) return;
        destroyed = true;
        // Stop tracking loops
        if (trackingRaf) { cancelAnimationFrame(trackingRaf); trackingRaf = 0; }
        // Unsubscribe chart events
        try {
          if (visibleRangeHandler && typeof timeScale.unsubscribeVisibleTimeRangeChange === 'function') {
            timeScale.unsubscribeVisibleTimeRangeChange(visibleRangeHandler);
          }
        } catch (_) {}
        try {
          if (logicalRangeHandler && typeof timeScale.unsubscribeVisibleLogicalRangeChange === 'function') {
            timeScale.unsubscribeVisibleLogicalRangeChange(logicalRangeHandler);
          }
        } catch (_) {}
        try {
          const rightScale = chart.priceScale && chart.priceScale('right');
          if (rightScale && priceSizeHandler && typeof rightScale.unsubscribeSizeChange === 'function') {
            rightScale.unsubscribeSizeChange(priceSizeHandler);
          }
        } catch (_) {}
        // Remove price lines we drew
        customPriceLineRefs.forEach((ref) => {
          try { candleSeries.removePriceLine(ref); } catch (_) {}
        });
        customPriceLineRefs = [];
        // DOM
        overlayEl.removeEventListener('click', onClick);
        containerEl.removeEventListener('pointerdown', onPointerDown);
        window.removeEventListener('pointerup', onPointerUp);
        window.removeEventListener('pointercancel', onPointerCancel);
        window.removeEventListener('blur', onBlur);
        containerEl.removeEventListener('wheel', onWheel);
        containerEl.removeEventListener('dblclick', onDblClick);
        window.removeEventListener('resize', onWindowResize);
        if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
        if (overlayEl.parentNode) overlayEl.parentNode.removeChild(overlayEl);
      },
    };
  };
})();