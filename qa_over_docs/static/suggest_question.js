document.addEventListener('DOMContentLoaded', function() {
    var buttons = document.querySelectorAll('.suggest-question-button');
    var destinationDiv = document.getElementById('suggest-question-modal-answer');
    var destinationInput = document.getElementById('suggest-question-answer-index');

    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            var sourceDivId = this.getAttribute('data-source');
            var sourceContent = document.getElementById(sourceDivId).innerHTML;
            destinationDiv.innerHTML = sourceContent;
            var index = sourceDivId.split("-")[1];
            destinationInput.value = index;
        });
    });
});