document.addEventListener('DOMContentLoaded', function() {
    var meetingIdInput = document.getElementById('meeting-id');
    var meetingForm = document.getElementById('joinMeetingForm');
    var joinButton = document.getElementById('joinMeetingButton');
    var loader = document.getElementById('loader');

    // Clean meeting ID input to remove any whitespace
    meetingIdInput.addEventListener('input', function() {
        this.value = this.value.replace(/\s+/g, '');
    });

    // Handle form submission
    meetingForm.addEventListener('submit', function(event) {
        event.preventDefault();
        loader.style.display = 'inline-block';
        joinButton.classList.add('disabled-button');

        var formData = new FormData(this);
        fetch('/enter_passcode', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        }).then(response => response.json())
          .then(body => {
            loader.style.display = 'none';
            joinButton.classList.remove('disabled-button');
            displayMessage(body.success, body.message);
          })
          .catch(error => {
            loader.style.display = 'none';
            joinButton.classList.remove('disabled-button');
            displayMessage(false, 'AI NOTE GENIUS has been notified !!! Will join meeting in few minutes');
          });
    });

    function displayMessage(success, message) {
        var alertBox = document.getElementById('alert-box');
        alertBox.innerHTML = `<div class="alert alert-${success ? 'success' : 'danger'} alert-dismissible fade show">
            <button type="button" class="close" data-dismiss="alert">&times;</button>
            ${message}
        </div>`;
        alertBox.style.display = 'block';
    }
});

