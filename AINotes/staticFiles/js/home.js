document.addEventListener('DOMContentLoaded', function() {
    // Storing user details in localStorage
    var userId = document.getElementById('userId').innerText;
    var userName = document.getElementById('userName').innerText;
    localStorage.setItem('userId', userId);
    localStorage.setItem('userName', userName);

    var uploadForm = document.getElementById('uploadForm');
    var transcribeButton = uploadForm.querySelector('button[type="submit"]');
    var transcribeLoader = document.getElementById('transcribeLoader');
    // var loadingOverlay = document.getElementById('loadingOverlay');

    const csrfToken = document.querySelector('input[name="csrf_token"]').value;


    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        transcribeLoader.style.display = 'inline-block'; // Show the loader
        transcribeButton.classList.add('disabled-button'); // Disable the button to prevent multiple submissions
        // loadingOverlay.style.display = 'block'; // Show the overlay

        var formData = new FormData(this);
        fetch('/transcribe', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
            headers: {
                // Adjust the header name according to your server-side framework's expected CSRF token header
                'X-CSRFToken': csrfToken
              }
        }).then(response => {
            transcribeLoader.style.display = 'none'; // Hide the loader
            transcribeButton.classList.remove('disabled-button'); // Enable the button
            // loadingOverlay.style.display = 'none'; // Hide the overlay
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Failed to transcribe file');
            }
        }).then(data => {
            if (data.success) {
                window.location.href = data.redirect_url; // Redirect if successful
            }
        }).catch(error => {
            console.error('Error:', error);
            alert('An error occurred while trying to transcribe the file.');
        });
    });

    function startMeeting(meetingLink) {
        window.open(meetingLink, '_blank').focus();
    }

    function copyToClipboard(text) {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);

        // Notify the user that the link has been copied
        const notification = document.createElement('div');
        notification.classList.add('copy-notification');
        notification.textContent = 'Link Copied!';
        document.body.appendChild(notification);
    }

    function confirmDelete(meetingId) {
        const confirmation = confirm("Are you sure you want to delete this meeting?");
        if (confirmation) {
            // User clicked OK, proceed with the deletion
            const form = document.querySelector(`form[action="/delete_scheduled_meeting"][data-meeting-id="${meetingId}"]`);
            if (form) {
                form.submit();
            }
        }
    }
});


