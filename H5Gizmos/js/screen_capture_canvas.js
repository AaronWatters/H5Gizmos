/*
Create a canvas for use in screen captures.

Assumes H5Canvas and jQueryUI.

Based on
https://developer.mozilla.org/en-US/docs/Web/API/Screen_Capture_API/Using_Screen_Capture

*/

(function () {

    class ScreenCapture extends H5Gizmos.DeferredValue {
        constructor(element) {
            super();
            debugger;
            var that = this;
            this.element = element;
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
            var err = (function (error) { that.reject(error); });
            var success = (function (stream) {that.handle_success(stream); });
            this.stream = null;var displayMediaOptions = {
                video: {
                  cursor: "always"
                },
                audio: false
            };
            navigator.mediaDevices.getDisplayMedia(displayMediaOptions).then(success).catch(err);
            //navigator.mediaDevices.getUserMedia(constraints).then(success).catch(err);
            element.screen_capture = this;
        };
        set_rectangle(x1, y1, x2, y2) {
            this.xmin = Math.min(x1, x2);
            this.xmax = Math.max(x1, x2);
            this.ymin = Math.min(y1, y2);
            this.ymax = Math.max(y1, y2);
        };
        handle_success(stream) {
            debugger;
            this.stream = stream;
            this.video.srcObject = stream;  
            this.load_stream();
        };
        get_size() {
            return [this.canvas.width, this.canvas.height];
        };
        load_stream() {
            debugger;
            var that = this;
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            var ctx = this.context;
            ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            ctx.fillStyle = "rgba(255, 0, 0, 0.4)";
            //ctx.fillStyle = "red";
            ctx.fillRect(this.xmin, this.ymin, this.xmax - this.xmin, this.ymax - this.ymin);
            requestAnimationFrame(function () { that.load_stream(); })
        };
    };

    H5Gizmos.screen_capture = function(element) {
        return new ScreenCapture(element);
    }

})();