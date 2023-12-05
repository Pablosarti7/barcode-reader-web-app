document.getElementById('myForm').onsubmit = function() {
    document.getElementById('loadingMessage').style.display = 'block';
};



document.getElementById('startbutton').addEventListener('click', function() {
    Quagga.init({
        inputStream: {
            type : "LiveStream",
            constraints: {
                width: 400,
                height: 400,
                facingMode: "environment" // or "user" for front camera
            },
            target: document.querySelector('#scanner-container'),
        },
        decoder: {
            readers : ["ean_reader"] // list of barcode types to look for
        },
        locate: true // enables barcode localization, which shows where in the image the barcode is detected
    }, function(err) {
        if (err) {
            console.log(err);
            return;
        }
        console.log("Initialization finished. Ready to start");
        Quagga.start();
    });

    let lastScannedBarcode = null;
    let debounceTimer = null;
    
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

            document.getElementById('loadingMessage').style.display = 'block';
            // Submit the form
            document.getElementById('barcodeForm').submit();
        }, 1000);
    });
});
