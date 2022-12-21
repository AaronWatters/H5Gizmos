/*
Canvas snapshot and screen capture support.

Assumes H5Canvas and jQueryUI.

Based on
https://developer.mozilla.org/en-US/docs/Web/API/Screen_Capture_API/Using_Screen_Capture

*/

(function () {

    /* moved to H5Gizmos.js as generally useful
    H5Gizmos.post_2d_canvas_image = function(end_point, dom_canvas, context2d, x, y, w, h, gizmo_translator) {
        // Send the image data from the canvas to the parent in a POST request
        context2d = context2d || dom_canvas.getContext("2d");
        x = x || 0;
        y = y || 0;
        w = w || canvas.width;
        h = h || canvas.height;
        // default to global interface
        gizmo_translator = gizmo_translator || H5GIZMO_INTERFACE;
        var image_data = context2d.getImageData(x, y, w, h);
        var json_metadata = {height: image_data.height, width: image_data.width};
        gizmo_translator.post_binary_data(end_point, image_data.data, json_metadata);
    };
    */

    // XXXX NOTE: This screen capture method only seems to work in recent versions of Chrome (not Firefox, Safari...)
    class ScreenCapture extends H5Gizmos.DeferredValue {
        constructor(element, size_callback, snap_callback, connect_media_now) {
            //console.log("size callback", size_callback)
            super();
            //debugger;
            var that = this;
            this.element = element;
            this.size_callback = size_callback;
            this.snap_callback = snap_callback;
            this.width = 0;
            this.height = 0;
            element.empty();
            this.$canvas = $("<canvas/>").appendTo(element);
            this.$video = $("<video autoplay/>");
            this.video = this.$video[0];
            //this.$video.appendTo(element);  // for debug only.
            this.canvas = this.$canvas[0];
            this.canvas.width = 480;
            this.canvas.height = 360;
            this.context = this.canvas.getContext("2d");
            this.context.font = "30px Arial";
            this.context.fillText("No window attached.", 10, 100);
            this.xmin = this.xmax = this.ymin = this.ymax = 0;
            this.stream = null;
            element.screen_capture = this;
            this.snapshot_list = null;
            this.all_snapshots_binary = null;
            this.all_snapshots_json = null;
            if (connect_media_now) {
                this.get_media();
            }
            // a version of get_media with correct "that" for use as a callback.
            this._get_media = function () { that.get_media(); };
        };
        get_media() {
            var that = this;
            var err = (function (error) { that.reject(error); });
            var success = (function (stream) {that.handle_success(stream); });
            this.stream = null;
            var displayMediaOptions = {
                video: {
                  cursor: "always",
                },
                audio: false
            };
            var media_getter;
            try {
                media_getter = navigator.mediaDevices.getDisplayMedia;
            } catch (e) {
                var warning = $(`<div style="color:red">
                getDisplayMedia is not available.  Please see
                <a href="https://stackoverflow.com/questions/56005165/navigator-getusermedia-and-navigator-webkitgetusermedia-undefined-after-updating">
                https://stackoverflow.com/questions/56005165/navigator-getusermedia-and-navigator-webkitgetusermedia-undefined-after-updating</a>
                for possible work-arounds.
                </div>`);
                warning.appendTo(this.element);
                throw e;
            }
            navigator.mediaDevices.getDisplayMedia(displayMediaOptions).then(success).catch(err);
            //navigator.mediaDevices.getUserMedia(constraints).then(success).catch(err);
            this.snapshot_list = null;
            this.all_snapshots_binary = null;
            this.all_snapshots_json = null;
        };
        set_rectangle(x1, y1, x2, y2) {
            this.xmin = Math.min(x1, x2);
            this.xmax = Math.max(x1, x2);
            this.ymin = Math.min(y1, y2);
            this.ymax = Math.max(y1, y2);
        };
        handle_success(stream) {
            //debugger;
            this.stream = stream;
            this.video.srcObject = stream;  
            this.load_stream();
            //this.get_size();
        };
        get_size() {
            var [width, height] = [this.canvas.width, this.canvas.height]
            this.width = width;
            this.height = height;
            if (this.size_callback) {
                console.log("calling size callback", width, height)
                this.size_callback(width, height)
            }
            return [width, height];
        };
        reset_snapshot_list() {
            this.snapshot_list = [];
            this.all_snapshots_binary = null;
            this.all_snapshots_json = null;
        };
        get_snapshot_list() {
            return this.snapshot_list;
        };
        snapshot(null_return) {
            //debugger
            // Get pixels under the currently highlighted region
            var ctx = this.context;
            var p = this.rectangle_parameters();
            var imgData = ctx.getImageData(p.x, p.y, p.w, p.h);
            var info = {height: imgData.height, width: imgData.width, data: imgData.data};
            if (this.snap_callback) {
                this.snap_callback(info)
            }
            if (this.snapshot_list != null) {
                this.snapshot_list.push(info)
            }
            if (!null_return) {
                return info;
            }
        };
        prepare_all_snapshots() {
            // Set up and validate data for POST of all snapshot data.
            // Return error message or null on success.
            this.all_snapshots_binary = null;
            this.all_snapshots_json = null;
            var snapshot_list = this.snapshot_list;
            if (!snapshot_list) {
                return "Snapshost list is not initialized.";
            }
            var nsnaps = snapshot_list.length;
            if (nsnaps < 1) {
                return "There are no snapshots.";
            }
            var snap0 = snapshot_list[0];
            var height = snap0.height;
            var width = snap0.width;
            var bands = 4;
            var snap_size = width * height * bands;
            var data_size = nsnaps * snap_size;
            try {
                var all_binary = new Uint8ClampedArray(data_size);
            } catch (error) {
                return "Could not combine frames -- too large?: " + error;
            }
            for (var i=0; i<nsnaps; i++) {
                var snap = snapshot_list[i];
                if (snap.width != width) {
                    return "Can't combine snapshots with width change " + [width, snap.width]
                }
                if (snap.height != height) {
                    return "Can't combine snapshots with height change " + [height, snap.height]
                }
                var offset = i * snap_size;
                var data = snap.data;
                all_binary.set(data, offset);
            }
            this.all_snapshots_binary = all_binary;
            this.all_snapshots_json = {
                height: height,
                width: width,
                count: nsnaps,
                bands: bands,
            }
            return null;   // No error: success
        };
        post_all_snapshots(to_endpoint, gizmo_translator) {
            // no automatic prepare for now.
            var binary = this.all_snapshots_binary;
            var json = this.all_snapshots_json;
            if (!binary || !json) {
                throw new Error("All snapshots must be prepared before posting.");
            }
            // default to global interface
            gizmo_translator = gizmo_translator || H5GIZMO_INTERFACE;
            gizmo_translator.post_binary_data(to_endpoint, binary, json);
        };
        post_snapshot(to_endpoint) {
            // Send a canvas snapshot using the POST method to the url endpoint.
            debugger;
            var canvas = this.canvas;
            var context = this.context;
            var p = this.rectangle_parameters();
            // xxx always use the global translator???
            H5Gizmos.post_2d_canvas_image(to_endpoint, canvas, context, p.x, p.y, p.w, p.h);
        };
        load_stream() {
            //debugger;
            var that = this;
            var width = this.canvas.width = this.video.videoWidth;
            var height = this.canvas.height = this.video.videoHeight;
            if ((this.width != width) || (this.height != height)) {
                this.get_size();
            }
            var ctx = this.context;
            ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            ctx.fillStyle = "rgba(255, 0, 0, 0.2)";
            //ctx.fillStyle = "red";
            var p = this.rectangle_parameters();
            ctx.fillRect(0, 0, p.x, p.max_h);
            ctx.fillRect(0, 0, p.max_w, p.y);
            ctx.fillRect(p.x + p.w, 0, p.max_w, p.max_h);
            ctx.fillRect(0, p.y + p.h, p.max_w, p.max_h);
            ctx.strokeStyle = "#999"
            ctx.strokeRect(p.x-1, p.y-1, p.w+2, p.h+2);
            requestAnimationFrame(function () { that.load_stream(); })
        };
        rectangle_parameters() {
            return {
                x: this.xmin, 
                y: this.ymin, 
                w: this.xmax - this.xmin, 
                h: this.ymax - this.ymin,
                max_w: this.canvas.width,
                max_h: this.canvas.height,
            }
        }
    };

    H5Gizmos.screen_capture = function(element, size_callback, snap_callback) {
        return new ScreenCapture(element, size_callback, snap_callback);
    }

})();