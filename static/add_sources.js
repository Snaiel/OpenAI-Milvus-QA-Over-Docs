// Get the file input and website input elements
const fileInput = document.getElementById('include-file');
const websiteInput = document.getElementById('include-url');
const includeSourceButton = document.getElementById('include-source');

// Add an event listener to check the inputs when they change
fileInput.addEventListener('change', toggleIncludeSourceButton);
websiteInput.addEventListener('input', toggleIncludeSourceButton);

function toggleIncludeSourceButton() {
    // Disable the button if both inputs are empty
    if (fileInput.value === '' && websiteInput.value === '') {
        includeSourceButton.disabled = true;
    } else {
        includeSourceButton.disabled = false;
    }
}

// // Show the modal when the page has finished loading
// document.addEventListener('DOMContentLoaded', function() {
//     var myModal = new bootstrap.Modal(document.getElementById('please-wait-modal'));
//     if (myModal != null) {
//         myModal.show();
//     }
//   });