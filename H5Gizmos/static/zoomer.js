(function attachZoomer(globalRoot) {
    class Zoomer {
        static DEFAULT_ZOOM_RATE = 1.2;
        static DEFAULT_REQUEST_THROTTLE_MS = 300;

        static isPositiveInteger(value) {
            return Number.isInteger(value) && value > 0;
        }

        static parseArrayShape(arrayShape) {
            if (!Array.isArray(arrayShape)) {
                throw new Error("array_shape must be an array.");
            }
            if (!(arrayShape.length === 2 || arrayShape.length === 3)) {
                throw new Error("array_shape must be [rows, cols], [rows, cols, 3], or [rows, cols, 4].");
            }
            const [rows, cols, channelsMaybe] = arrayShape;
            if (!Zoomer.isPositiveInteger(rows) || !Zoomer.isPositiveInteger(cols)) {
                throw new Error("array_shape rows and columns must be positive integers.");
            }
            let channels = 1;
            if (arrayShape.length === 3) {
                if (!(channelsMaybe === 3 || channelsMaybe === 4)) {
                    throw new Error("array_shape third dimension must be 3 (RGB) or 4 (RGBA).");
                }
                channels = channelsMaybe;
            }
            return { rows, cols, channels };
        }

        static parseConfig(configMaybe) {
            if (configMaybe === undefined) {
                return { requestThrottleMs: Zoomer.DEFAULT_REQUEST_THROTTLE_MS };
            }
            if (typeof configMaybe === "number") {
                if (!Number.isFinite(configMaybe) || configMaybe < 0) {
                    throw new Error("requestThrottleMs must be a finite number >= 0.");
                }
                return { requestThrottleMs: configMaybe };
            }
            if (!configMaybe || typeof configMaybe !== "object") {
                throw new Error("options must be a number or object.");
            }
            const requestThrottleMs = configMaybe.requestThrottleMs ?? Zoomer.DEFAULT_REQUEST_THROTTLE_MS;
            if (!Number.isFinite(requestThrottleMs) || requestThrottleMs < 0) {
                throw new Error("options.requestThrottleMs must be a finite number >= 0.");
            }
            return { requestThrottleMs };
        }

        static clamp(value, minValue, maxValue) {
            return Math.min(maxValue, Math.max(minValue, value));
        }

        static sameViewport(a, b) {
            return a.rowStart === b.rowStart &&
                a.rowStop === b.rowStop &&
                a.colStart === b.colStart &&
                a.colStop === b.colStop;
        }

        static toIntegerViewport(viewport, rows, cols) {
            const rowStart = Zoomer.clamp(Math.round(viewport.rowStart), 0, rows - 1);
            const rowStop = Zoomer.clamp(Math.round(viewport.rowStop), rowStart + 1, rows);
            const colStart = Zoomer.clamp(Math.round(viewport.colStart), 0, cols - 1);
            const colStop = Zoomer.clamp(Math.round(viewport.colStop), colStart + 1, cols);
            return { rowStart, rowStop, colStart, colStop };
        }

        static fitDimensions(sourceWidth, sourceHeight, maxWidth, maxHeight) {
            const scale = Math.min(maxWidth / sourceWidth, maxHeight / sourceHeight);
            let width = Math.max(1, Math.round(sourceWidth * scale));
            let height = Math.max(1, Math.round(sourceHeight * scale));
            while (width > maxWidth) {
                width -= 1;
            }
            while (height > maxHeight) {
                height -= 1;
            }
            return { width, height };
        }

        static getFittedRect(sourceWidth, sourceHeight, outerWidth, outerHeight) {
            const fitted = Zoomer.fitDimensions(sourceWidth, sourceHeight, outerWidth, outerHeight);
            return {
                x: (outerWidth - fitted.width) / 2,
                y: (outerHeight - fitted.height) / 2,
                width: fitted.width,
                height: fitted.height
            };
        }

        static convertToRgba(u8, width, height, channels) {
            const pixelCount = width * height;
            const rgba = new Uint8ClampedArray(pixelCount * 4);
            if (channels === 4) {
                rgba.set(u8);
                return rgba;
            }
            if (channels === 3) {
                for (let i = 0, j = 0; i < pixelCount; i += 1, j += 3) {
                    const k = i * 4;
                    rgba[k] = u8[j];
                    rgba[k + 1] = u8[j + 1];
                    rgba[k + 2] = u8[j + 2];
                    rgba[k + 3] = 255;
                }
                return rgba;
            }
            for (let i = 0; i < pixelCount; i += 1) {
                const v = u8[i];
                const k = i * 4;
                rgba[k] = v;
                rgba[k + 1] = v;
                rgba[k + 2] = v;
                rgba[k + 3] = 255;
            }
            return rgba;
        }

        static validateDimensions(width, height, namePrefix) {
            if (!Zoomer.isPositiveInteger(width) || !Zoomer.isPositiveInteger(height)) {
                console.error(`${namePrefix} width:`, width, "height:", height);
                throw new Error(`${namePrefix} width and height must be positive integers.`);
            }
        }

        static stepFromFloat(value) {
            if (value > 0) {
                return Math.floor(value);
            }
            if (value < 0) {
                return Math.ceil(value);
            }
            return 0;
        }

        static getAnimationFrameFns() {
            if (typeof requestAnimationFrame === "function" && typeof cancelAnimationFrame === "function") {
                return {
                    request: requestAnimationFrame.bind(globalThis),
                    cancel: cancelAnimationFrame.bind(globalThis)
                };
            }
            return {
                request: (cb) => setTimeout(() => cb(Date.now()), 16),
                cancel: (id) => clearTimeout(id)
            };
        }

        static get testables() {
            return {
                parseArrayShape: Zoomer.parseArrayShape,
                parseConfig: Zoomer.parseConfig,
                fitDimensions: Zoomer.fitDimensions,
                getFittedRect: Zoomer.getFittedRect,
                convertToRgba: Zoomer.convertToRgba,
                toIntegerViewport: Zoomer.toIntegerViewport,
                stepFromFloat: Zoomer.stepFromFloat
            };
        }

        constructor(domElement, updateRequestCallback, width, height, arrayShape, options) {
            // debug: list the arguments
            //console.log("domElement:", domElement);
            //console.log("updateRequestCallback:", updateRequestCallback);
            //console.log("width:", width, "height:", height);
            //console.log("arrayShape:", arrayShape);
            //console.log("options:", options);
            if (!domElement || typeof domElement.appendChild !== "function") {
                throw new Error("dom_element must be a valid DOM element.");
            }
            if (typeof updateRequestCallback !== "function") {
                throw new Error("update_request_callback must be a function.");
            }
            Zoomer.validateDimensions(width, height, "Canvas");
            const shape = Zoomer.parseArrayShape(arrayShape);
            const config = Zoomer.parseConfig(options);

            this.zoomRate = Zoomer.DEFAULT_ZOOM_RATE;
            this.requestThrottleMs = config.requestThrottleMs;
            this.domElement = domElement;
            this.updateRequestCallback = updateRequestCallback;
            this.canvasWidth = width;
            this.canvasHeight = height;
            this.arrayRows = shape.rows;
            this.arrayCols = shape.cols;
            this.channels = shape.channels;
            this.destroyed = false;

            this.desiredViewport = {
                rowStart: 0,
                rowStop: this.arrayRows,
                colStart: 0,
                colStop: this.arrayCols
            };

            this.nextRequestId = 1;
            this.latestIssuedRequest = null;
            this.lastRequestIssuedAt = -Infinity;
            this.trailingRequestPending = false;
            this.throttleTimeoutHandle = null;

            this.cachedPanel = null;
            this.previewFrameHandle = null;
            this.clickCallback = null;

            this.pointerCaptureId = null;
            this.dragState = null;

            const doc = domElement.ownerDocument || globalThis.document;
            if (!doc || typeof doc.createElement !== "function") {
                throw new Error("Unable to create canvas: document is unavailable.");
            }
            this.canvas = doc.createElement("canvas");
            this.canvas.width = width;
            this.canvas.height = height;
            this.canvas.style.width = `${width}px`;
            this.canvas.style.height = `${height}px`;
            this.canvas.style.display = "block";
            this.canvas.style.touchAction = "none";

            const context = this.canvas.getContext("2d");
            if (!context) {
                throw new Error("Unable to acquire 2D canvas context.");
            }
            this.context = context;

            this.cachedCanvas = doc.createElement("canvas");
            this.cachedContext = this.cachedCanvas.getContext("2d");
            if (!this.cachedContext) {
                throw new Error("Unable to acquire cached-image 2D canvas context.");
            }

            const rafFns = Zoomer.getAnimationFrameFns();
            this.requestAnimationFrame = rafFns.request;
            this.cancelAnimationFrame = rafFns.cancel;

            this.onPointerDown = this._onPointerDown.bind(this);
            this.onPointerMove = this._onPointerMove.bind(this);
            this.onPointerUp = this._onPointerUp.bind(this);
            this.onPointerCancel = this._onPointerCancel.bind(this);
            this.onWheel = this._onWheel.bind(this);
            this.onClick = this._onClick.bind(this);

            this.canvas.addEventListener("pointerdown", this.onPointerDown);
            this.canvas.addEventListener("pointermove", this.onPointerMove);
            this.canvas.addEventListener("pointerup", this.onPointerUp);
            this.canvas.addEventListener("pointercancel", this.onPointerCancel);
            this.canvas.addEventListener("wheel", this.onWheel, { passive: false });
            this.canvas.addEventListener("click", this.onClick);
            this.domElement.appendChild(this.canvas);

            this._issueRequestForDesiredViewport();
            this._schedulePreviewRedraw();
        }

        _now() {
            return Date.now();
        }

        _getViewportSize(viewport) {
            return {
                rows: viewport.rowStop - viewport.rowStart,
                cols: viewport.colStop - viewport.colStart
            };
        }

        _getDesiredDisplayRect() {
            const size = this._getViewportSize(this.desiredViewport);
            return Zoomer.getFittedRect(size.cols, size.rows, this.canvasWidth, this.canvasHeight);
        }

        _computeRequestOutputSize(viewport) {
            const size = this._getViewportSize(viewport);
            const fitted = Zoomer.fitDimensions(size.cols, size.rows, this.canvasWidth, this.canvasHeight);
            return { outputWidth: fitted.width, outputHeight: fitted.height };
        }

        _schedulePreviewRedraw() {
            if (this.destroyed || this.previewFrameHandle !== null) {
                return;
            }
            this.previewFrameHandle = this.requestAnimationFrame(() => {
                this.previewFrameHandle = null;
                this._drawFromCacheAgainstDesiredViewport();
            });
        }

        _drawFromCacheAgainstDesiredViewport() {
            this.context.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
            if (!this.cachedPanel) {
                return;
            }

            const desired = this.desiredViewport;
            const desiredSize = this._getViewportSize(desired);
            if (desiredSize.rows <= 0 || desiredSize.cols <= 0) {
                return;
            }
            const displayRect = this._getDesiredDisplayRect();
            const cached = this.cachedPanel;
            const cachedBounds = cached.bounds;

            const overlapRowStart = Math.max(desired.rowStart, cachedBounds.rowStart);
            const overlapRowStop = Math.min(desired.rowStop, cachedBounds.rowStop);
            const overlapColStart = Math.max(desired.colStart, cachedBounds.colStart);
            const overlapColStop = Math.min(desired.colStop, cachedBounds.colStop);
            if (overlapRowStart >= overlapRowStop || overlapColStart >= overlapColStop) {
                return;
            }

            const cachedRows = cachedBounds.rowStop - cachedBounds.rowStart;
            const cachedCols = cachedBounds.colStop - cachedBounds.colStart;
            const srcX = ((overlapColStart - cachedBounds.colStart) / cachedCols) * cached.width;
            const srcY = ((overlapRowStart - cachedBounds.rowStart) / cachedRows) * cached.height;
            const srcW = ((overlapColStop - overlapColStart) / cachedCols) * cached.width;
            const srcH = ((overlapRowStop - overlapRowStart) / cachedRows) * cached.height;

            const dstX = displayRect.x + ((overlapColStart - desired.colStart) / desiredSize.cols) * displayRect.width;
            const dstY = displayRect.y + ((overlapRowStart - desired.rowStart) / desiredSize.rows) * displayRect.height;
            const dstW = ((overlapColStop - overlapColStart) / desiredSize.cols) * displayRect.width;
            const dstH = ((overlapRowStop - overlapRowStart) / desiredSize.rows) * displayRect.height;

            this.context.save();
            this.context.beginPath();
            this.context.rect(displayRect.x, displayRect.y, displayRect.width, displayRect.height);
            this.context.clip();
            this.context.imageSmoothingEnabled = false;
            this.context.drawImage(
                this.cachedCanvas,
                srcX,
                srcY,
                srcW,
                srcH,
                dstX,
                dstY,
                dstW,
                dstH
            );
            this.context.restore();
        }

        _issueRequestForDesiredViewport() {
            if (this.destroyed) {
                return;
            }
            const viewport = this.desiredViewport;
            const { outputHeight, outputWidth } = this._computeRequestOutputSize(viewport);
            const requestId = this.nextRequestId;
            this.nextRequestId += 1;
            const req = {
                rowStart: viewport.rowStart,
                rowStop: viewport.rowStop,
                colStart: viewport.colStart,
                colStop: viewport.colStop,
                outputHeight,
                outputWidth,
                requestId
            };
            this.latestIssuedRequest = req;
            this.lastRequestIssuedAt = this._now();
            this.trailingRequestPending = false;
            this.updateRequestCallback(
                req.rowStart,
                req.rowStop,
                req.colStart,
                req.colStop,
                req.outputHeight,
                req.outputWidth,
                req.requestId
            );
        }

        _scheduleThrottledRequest() {
            if (this.destroyed) {
                return;
            }
            const now = this._now();
            const elapsed = now - this.lastRequestIssuedAt;
            if (elapsed >= this.requestThrottleMs) {
                this._issueRequestForDesiredViewport();
                return;
            }
            this.trailingRequestPending = true;
            if (this.throttleTimeoutHandle !== null) {
                return;
            }
            const wait = this.requestThrottleMs - elapsed;
            this.throttleTimeoutHandle = setTimeout(() => {
                this.throttleTimeoutHandle = null;
                if (this.destroyed || !this.trailingRequestPending) {
                    return;
                }
                this._issueRequestForDesiredViewport();
            }, wait);
        }

        _setDesiredViewportIfChanged(nextViewport) {
            const integerViewport = Zoomer.toIntegerViewport(nextViewport, this.arrayRows, this.arrayCols);
            if (Zoomer.sameViewport(this.desiredViewport, integerViewport)) {
                return false;
            }
            this.desiredViewport = integerViewport;
            this._schedulePreviewRedraw();
            this._scheduleThrottledRequest();
            return true;
        }

        _eventPointInCanvas(event) {
            const rect = this.canvas.getBoundingClientRect();
            return {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
        }

        _pointInRect(point, rect) {
            return point.x >= rect.x &&
                point.y >= rect.y &&
                point.x <= rect.x + rect.width &&
                point.y <= rect.y + rect.height;
        }

        _onWheel(event) {
            if (this.destroyed) {
                return;
            }
            const point = this._eventPointInCanvas(event);
            const rect = this._getDesiredDisplayRect();
            if (!this._pointInRect(point, rect)) {
                return;
            }
            event.preventDefault();
            const normalizedX = (point.x - rect.x) / rect.width;
            const normalizedY = (point.y - rect.y) / rect.height;
            const size = this._getViewportSize(this.desiredViewport);
            const anchorRow = this.desiredViewport.rowStart + normalizedY * size.rows;
            const anchorCol = this.desiredViewport.colStart + normalizedX * size.cols;

            const zoomDirection = Math.sign(event.deltaY);
            if (zoomDirection === 0) {
                return;
            }
            const scaleFactor = zoomDirection < 0 ? this.zoomRate : (1 / this.zoomRate);
            const currentArrayPixelsPerScreenPixel = rect.width / size.cols;
            const minArrayPixelsPerScreenPixel = Math.min(
                this.canvasWidth / this.arrayCols,
                this.canvasHeight / this.arrayRows
            );
            const nextArrayPixelsPerScreenPixel = Math.max(
                minArrayPixelsPerScreenPixel,
                currentArrayPixelsPerScreenPixel * scaleFactor
            );
            const nextRows = Zoomer.clamp(
                Math.round(this.canvasHeight / nextArrayPixelsPerScreenPixel),
                1,
                this.arrayRows
            );
            const nextCols = Zoomer.clamp(
                Math.round(this.canvasWidth / nextArrayPixelsPerScreenPixel),
                1,
                this.arrayCols
            );

            const unclampedRowStart = Math.round(anchorRow - normalizedY * nextRows);
            const unclampedColStart = Math.round(anchorCol - normalizedX * nextCols);
            const rowStart = Zoomer.clamp(unclampedRowStart, 0, this.arrayRows - nextRows);
            const colStart = Zoomer.clamp(unclampedColStart, 0, this.arrayCols - nextCols);
            const nextViewport = {
                rowStart,
                rowStop: rowStart + nextRows,
                colStart,
                colStop: colStart + nextCols
            };
            this._setDesiredViewportIfChanged(nextViewport);
        }

        _onPointerDown(event) {
            if (this.destroyed) {
                return;
            }
            if (event.button !== 0) {
                return;
            }
            const point = this._eventPointInCanvas(event);
            const rect = this._getDesiredDisplayRect();
            if (!this._pointInRect(point, rect)) {
                return;
            }
            const size = this._getViewportSize(this.desiredViewport);
            this.dragState = {
                pointerId: event.pointerId,
                lastX: event.clientX,
                lastY: event.clientY,
                rowPerPixel: size.rows / rect.height,
                colPerPixel: size.cols / rect.width,
                residualRowShift: 0,
                residualColShift: 0
            };
            this.pointerCaptureId = event.pointerId;
            this.canvas.setPointerCapture(event.pointerId);
        }

        _onPointerMove(event) {
            if (this.destroyed || !this.dragState || event.pointerId !== this.dragState.pointerId) {
                return;
            }
            const dx = event.clientX - this.dragState.lastX;
            const dy = event.clientY - this.dragState.lastY;
            this.dragState.lastX = event.clientX;
            this.dragState.lastY = event.clientY;

            this.dragState.residualRowShift += -dy * this.dragState.rowPerPixel;
            this.dragState.residualColShift += -dx * this.dragState.colPerPixel;

            const rowStep = Zoomer.stepFromFloat(this.dragState.residualRowShift);
            const colStep = Zoomer.stepFromFloat(this.dragState.residualColShift);
            if (rowStep === 0 && colStep === 0) {
                return;
            }
            this.dragState.residualRowShift -= rowStep;
            this.dragState.residualColShift -= colStep;

            const size = this._getViewportSize(this.desiredViewport);
            const nextRowStart = Zoomer.clamp(this.desiredViewport.rowStart + rowStep, 0, this.arrayRows - size.rows);
            const nextColStart = Zoomer.clamp(this.desiredViewport.colStart + colStep, 0, this.arrayCols - size.cols);
            const nextViewport = {
                rowStart: nextRowStart,
                rowStop: nextRowStart + size.rows,
                colStart: nextColStart,
                colStop: nextColStart + size.cols
            };
            this._setDesiredViewportIfChanged(nextViewport);
        }

        _clearDragState() {
            this.dragState = null;
            this.pointerCaptureId = null;
        }

        _onPointerUp(event) {
            if (this.destroyed || !this.dragState || event.pointerId !== this.dragState.pointerId) {
                return;
            }
            if (this.pointerCaptureId !== null && this.canvas.hasPointerCapture(this.pointerCaptureId)) {
                this.canvas.releasePointerCapture(this.pointerCaptureId);
            }
            this._clearDragState();
        }

        _onPointerCancel(event) {
            if (this.destroyed || !this.dragState || event.pointerId !== this.dragState.pointerId) {
                return;
            }
            if (this.pointerCaptureId !== null && this.canvas.hasPointerCapture(this.pointerCaptureId)) {
                this.canvas.releasePointerCapture(this.pointerCaptureId);
            }
            this._clearDragState();
        }

        _onClick(event) {
            if (this.destroyed || typeof this.clickCallback !== "function") {
                return;
            }
            const point = this._eventPointInCanvas(event);
            const rect = this._getDesiredDisplayRect();
            if (!this._pointInRect(point, rect)) {
                return;
            }
            const size = this._getViewportSize(this.desiredViewport);
            const normalizedX = (point.x - rect.x) / rect.width;
            const normalizedY = (point.y - rect.y) / rect.height;
            const colOffset = Math.min(size.cols - 1, Math.floor(normalizedX * size.cols));
            const rowOffset = Math.min(size.rows - 1, Math.floor(normalizedY * size.rows));
            const row = this.desiredViewport.rowStart + rowOffset;
            const col = this.desiredViewport.colStart + colOffset;
            this.clickCallback(row, col);
        }

        update(uint8array, width, height, requestId) {
            if (this.destroyed) {
                return false;
            }
            if (!this.latestIssuedRequest || requestId !== this.latestIssuedRequest.requestId) {
                return false;
            }
            if (!(uint8array instanceof Uint8Array || uint8array instanceof Uint8ClampedArray)) {
                throw new Error("update() requires Uint8Array or Uint8ClampedArray.");
            }
            Zoomer.validateDimensions(width, height, "update()");
            const expectedLength = width * height * this.channels;
            if (uint8array.length !== expectedLength) {
                throw new Error(`update() data length mismatch: expected ${expectedLength}, got ${uint8array.length}.`);
            }
            const rgba = Zoomer.convertToRgba(uint8array, width, height, this.channels);
            let imageData;
            if (typeof ImageData === "function") {
                imageData = new ImageData(rgba, width, height);
            } else {
                imageData = this.cachedContext.createImageData(width, height);
                imageData.data.set(rgba);
            }
            this.cachedCanvas.width = width;
            this.cachedCanvas.height = height;
            this.cachedContext.putImageData(imageData, 0, 0);

            this.cachedPanel = {
                width,
                height,
                bounds: {
                    rowStart: this.latestIssuedRequest.rowStart,
                    rowStop: this.latestIssuedRequest.rowStop,
                    colStart: this.latestIssuedRequest.colStart,
                    colStop: this.latestIssuedRequest.colStop
                },
                requestId
            };
            this._drawFromCacheAgainstDesiredViewport();
            return true;
        }

        reset() {
            if (this.destroyed) {
                return;
            }
            const resetViewport = {
                rowStart: 0,
                rowStop: this.arrayRows,
                colStart: 0,
                colStop: this.arrayCols
            };
            this._setDesiredViewportIfChanged(resetViewport);
        }

        reload() {
            if (this.destroyed) {
                return;
            }
            this.trailingRequestPending = false;
            if (this.throttleTimeoutHandle !== null) {
                clearTimeout(this.throttleTimeoutHandle);
                this.throttleTimeoutHandle = null;
            }
            this._issueRequestForDesiredViewport();
        }

        on_click_callback(cb) {
            if (cb !== null && typeof cb !== "function") {
                throw new Error("on_click_callback(cb) requires a function or null.");
            }
            this.clickCallback = cb;
        }

        destroy() {
            if (this.destroyed) {
                return;
            }
            this.destroyed = true;
            this.canvas.removeEventListener("pointerdown", this.onPointerDown);
            this.canvas.removeEventListener("pointermove", this.onPointerMove);
            this.canvas.removeEventListener("pointerup", this.onPointerUp);
            this.canvas.removeEventListener("pointercancel", this.onPointerCancel);
            this.canvas.removeEventListener("wheel", this.onWheel);
            this.canvas.removeEventListener("click", this.onClick);
            if (this.previewFrameHandle !== null) {
                this.cancelAnimationFrame(this.previewFrameHandle);
                this.previewFrameHandle = null;
            }
            if (this.throttleTimeoutHandle !== null) {
                clearTimeout(this.throttleTimeoutHandle);
                this.throttleTimeoutHandle = null;
            }
            if (this.pointerCaptureId !== null && this.canvas.hasPointerCapture(this.pointerCaptureId)) {
                this.canvas.releasePointerCapture(this.pointerCaptureId);
            }
            this._clearDragState();
            if (this.canvas.parentNode === this.domElement) {
                this.domElement.removeChild(this.canvas);
            }
        }
    }

    globalRoot.Zoomer = Zoomer;

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { Zoomer };
    }
}(typeof globalThis !== "undefined" ? globalThis : this));
