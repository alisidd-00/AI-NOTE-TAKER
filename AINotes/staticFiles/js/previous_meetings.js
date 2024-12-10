$(document).ready(function() {
    // Initialize DataTables
    var table = $('#dataTable').DataTable();
    var upcomingTable = $('#scheduledMeetingsTable').DataTable();
    var filesTable = $('#uploadedFilesTable').DataTable({
        "responsive": true,
        "paging": true,
        "searching": true,
        "info": true
    });

    // Event delegation for dynamically generated share buttons
    document.body.addEventListener("click", function(event) {
        if (event.target.classList.contains("share-button")) {
            event.preventDefault();
            const link = event.target.getAttribute("data-link");
            copyToClipboard(link);
            showFlashMessage("URL has been copied to the clipboard.");
        }
    });

    // Copy to clipboard functionality
    function copyToClipboard(text) {
        const tempInput = document.createElement("input");
        tempInput.value = text;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
    }

    // Flash message display function
    function showFlashMessage(message) {
        const flashMessageContainer = document.getElementById("flash-message-container");
        flashMessageContainer.innerHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `;
    }

    function refreshMeetingsData() {
        $.ajax({
            url: '/previous-meetings',  // Change the URL to whatever your new endpoint is
            type: "GET",
            success: function(response) {
                // Assuming the response contains HTML content for each tab
                $('#upcoming').html($(response).find('#upcoming').html());
                $('#occurred').html($(response).find('#occurred').html());
                $('#file').html($(response).find('#file').html());
            },
            error: function() {
                console.error('Failed to fetch updated meetings data.');
            }
        });
    }
    
    // Set interval for polling
    setInterval(refreshMeetingsData, 15000); // Adjust time as necessary
    
    // Event delegation for form submissions
    $(document).on('submit', 'form[id^="activateForm"]', function(event) {
        event.preventDefault(); // Prevent default form submission
        const $form = $(this); // Get the form that was submitted
        const $button = $form.find('button'); // Find the button in the form
        const $spinner = $button.find('.spinner-border'); // Find the spinner

        $spinner.show();

        const formData = $(this).serialize(); // Serialize form data

        $.ajax({
            url: '/enter_passcode',
            type: 'POST',
            timeout: 60000, // Timeout set to 60 seconds
            data: formData, // Send serialized form data
            success: function(data) {
                $spinner.hide(); 
                showFlashMessage("Bot has been initatied");
                // console.log('Server response:', data.message);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $spinner.hide(); 
                showFlashMessage("Bot has been initatied");
                // console.error("AJAX error:", textStatus); // Log errors
            }
        });
    });
});

