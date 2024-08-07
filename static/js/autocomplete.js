var inputElement = document.getElementById("textbox");
var resultBox = document.querySelector('.result-box');

let delayTimer = null;

inputElement.addEventListener("keyup", function (event) {
    var textBoxValue = inputElement.value;

    const query = encodeURIComponent(textBoxValue);

    clearTimeout(delayTimer);

    delayTimer = setTimeout(function() {

        fetch(`http://127.0.0.1:5000/search-suggestions?q=${query}`)
            .then(response => response.json())
            .then(data => {

                let result = [];
                let input = inputElement.value;

                if (input.length) {
                    result = data['suggestions'].filter((keyword) => {
                        return keyword.toLowerCase().includes(input.toLowerCase());
                    })
                }
                console.log(result);
                display(result);
            })
            .catch(error => {
                console.error("Error:", error);
            });

    }, 2000);

});

// displaying the suggestion on the result-box div
function display(result) {
    const content = result.map((list) => {
        return "<div onclick=selectInput(this)>" + list + "</div>";
    });
    resultBox.innerHTML = content.join('');
}

function selectInput(list) {
    inputElement.value = list.innerHTML;
    resultBox.innerHTML = '';
}
