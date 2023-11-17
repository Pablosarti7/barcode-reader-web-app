// document.getElementById('startbutton').addEventListener('click', function() {
//     Quagga.init({
//         inputStream: {
//             type : "LiveStream",
//             constraints: {
//                 width: 640,
//                 height: 480,
//                 facingMode: "environment" // or "user" for front camera
//             }
//         },
//         decoder: {
//             readers : ["ean_reader"] // list of barcode types to look for
//         },
//         locate: true // enables barcode localization, which shows where in the image the barcode is detected
//     }, function(err) {
//         if (err) {
//             console.log(err);
//             return;
//         }
//         console.log("Initialization finished. Ready to start");
//         Quagga.start();
//     });

//     Quagga.onDetected(function(data) {
        
//         fetch('/barcode', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({barcode: data.codeResult.code}),
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 window.location.href = '/product?barcode=' + data.barcode;
//             }
//         })        
//         .catch((error) => {
//             console.error('Error:', error);
//         });
                
//     });

// });
