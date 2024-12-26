document.getElementById('startbutton').addEventListener('click', function() {
    // Initializing camera feed.
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#scanner-container'),
            constraints: {
                facingMode: "environment",
                focusMode: "continuous"  // Add this line for auto focus
            },
        },
        decoder: {
            readers: [
                "code_128_reader",
                "ean_reader",
                "ean_8_reader",
                "code_39_reader",
                "code_39_vin_reader",
                "codabar_reader",
                "upc_reader",
                "upc_e_reader",
                "i2of5_reader"
            ],
            debug: {
                showCanvas: true,
                showPatches: true,
                showFoundPatches: true,
                showSkeleton: true,
                showLabels: true,
                showPatchLabels: true,
                showRemainingPatchLabels: true,
                boxFromPatches: {
                    showTransformed: true,
                    showTransformedBox: true,
                    showBB: true
                }
            }
        },

    }, function (err) {
        if (err) {
            console.log(err);
            return
        }
        console.log("Initialization finished. Ready to start");
        Quagga.start();
        document.getElementById('cameraModal').style.display = 'block';
    });

    // Drawing squares and rectangles for the camera.
    Quagga.onProcessed(function (result) {
        var drawingCtx = Quagga.canvas.ctx.overlay,
        drawingCanvas = Quagga.canvas.dom.overlay;

        if (result) {
            if (result.boxes) {
                drawingCtx.clearRect(0, 0, parseInt(drawingCanvas.getAttribute("width")), parseInt(drawingCanvas.getAttribute("height")));
                result.boxes.filter(function (box) {
                    return box !== result.box;
                }).forEach(function (box) {
                    Quagga.ImageDebug.drawPath(box, { x: 0, y: 1 }, drawingCtx, { color: "green", lineWidth: 2 });
                });
            }

            if (result.box) {
                Quagga.ImageDebug.drawPath(result.box, { x: 0, y: 1 }, drawingCtx, { color: "#00F", lineWidth: 2 });
            }

            if (result.codeResult && result.codeResult.code) {
                Quagga.ImageDebug.drawPath(result.line, { x: 'x', y: 'y' }, drawingCtx, { color: 'red', lineWidth: 3 });
            }
        }
    });

    // Get the modal
    var modal = document.getElementById("cameraModal");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("close")[0];

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        modal.style.display = "none";
        Quagga.stop();
    };

    // Close the modal if the user clicks anywhere outside of it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
            Quagga.stop();
        }
    };

    // Detecting barcode
    let lastScannedBarcode = null;
    let debounceTimer = null;

    // Scanning for barcode and submitting form.
    Quagga.onDetected(function(data) {
        const scannedBarcode = data.codeResult.code;
        // Check if the new barcode is the same as the last scanned one
        if (scannedBarcode === lastScannedBarcode) {
            return;
        }

        lastScannedBarcode = scannedBarcode;

        // Clear the existing debounce timer
        clearTimeout(debounceTimer);

        debounceTimer = setTimeout(function() {
            // Set the barcode value to the hidden form input
            document.getElementById('hiddenBarcodeInput').value = scannedBarcode;
            modal.style.display = "none";
            // Submit the form
            document.getElementById('barcodeForm').submit();
        }, 5000);
    });

    // Draw a reference rectangle on the camera feed
    var scannerContainer = document.querySelector('#scanner-container');
    var referenceRect = document.createElement('div');
    referenceRect.style.position = 'absolute';
    referenceRect.style.border = '3px solid red';
    referenceRect.style.width = '80%';
    referenceRect.style.height = '50%';
    referenceRect.style.zIndex = '1000';                                                                                                                        
    scannerContainer.appendChild(referenceRect);

    // Add touch-to-focus functionality
    scannerContainer.addEventListener('click', function(event) {
        var videoTrack = Quagga.CameraAccess.getActiveTrack();
        if (videoTrack && typeof videoTrack.getCapabilities === 'function') {
            var capabilities = videoTrack.getCapabilities();
            if (capabilities.focusMode) {
                videoTrack.applyConstraints({
                    advanced: [{ focusMode: 'auto', 
                        pointsOfInterest: [{ 
                            x: event.offsetX / scannerContainer.clientWidth, 
                            y: event.offsetY / scannerContainer.clientHeight 
                        }] 
                    }]
                });
            }
        }
    });
});
