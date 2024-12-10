// Time in milliseconds after which the user will be logged out due to inactivity. For example, 900000 ms for 15 minutes.
const TIMEOUT_PERIOD = 1800000; 
let logoutTimer;

// Function to reset the logout timer
function resetTimer() {
    // clearTimeout(logoutTimer);
    logoutTimer = setTimeout(showTimeoutMessageAndLogout, TIMEOUT_PERIOD);
}

function showTimeoutMessageAndLogout() {
    // Display the custom modal using Bootstrap's modal method
    $('#timeoutModal').modal('show');

    // Setup the event handler for the OK button to redirect and then hide the modal
    document.getElementById('logoutButton').onclick = function() {
        window.location.href = '/logout'; // Redirect to Flask logout route
    };
}

//     // Handle the modal's 'hidden' event to reset the timer if the modal is dismissed by other means
//     $('#timeoutModal').on('hidden.bs.modal', function () {
//         resetTimer();
//     });
// }

// // Event listeners for various user actions to reset the timer
// document.addEventListener('mousemove', resetTimer, false);
// document.addEventListener('keydown', resetTimer, false);
// document.addEventListener('click', resetTimer, false);
// document.addEventListener('scroll', resetTimer, false);

// Reset the timer initially when the script loads
resetTimer();

    