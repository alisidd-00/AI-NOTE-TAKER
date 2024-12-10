document.addEventListener('DOMContentLoaded', function() {
    function getPercentageValue(elementId, defaultValue) {
        var value = parseFloat(document.getElementById(elementId).value);
        return isNaN(value) ? defaultValue : value;
    }

    var positivePercentage = getPercentageValue('positivePercentage', 0);
    var negativePercentage = getPercentageValue('negativePercentage', 0);
    var neutralPercentage = getPercentageValue('neutralPercentage', 100);

    var total = positivePercentage + negativePercentage + neutralPercentage;
    if (total === 0) {
        positivePercentage = 0;
        negativePercentage = 0;
        neutralPercentage = 100;
    }

    var data = [{
        values: [positivePercentage, negativePercentage, neutralPercentage],
        labels: ['Positive', 'Negative', 'Neutral'],
        type: 'pie',
        hole: 0.4,
        textinfo: 'percent',
        textposition: 'inside',
        automargin: true
    }];

    var layout = {
        height: 300,
        width: 350,
        showlegend: true
    };

    Plotly.newPlot('sentimentChart', data, layout);
});

function showToast(message, isSuccess = true) {
    const toastElement = document.getElementById('toast');
    const toastBody = toastElement.querySelector('.toast-body');
    const toastHeader = toastElement.querySelector('.toast-header');

    toastBody.textContent = message; // Set the toast message dynamically
    toastHeader.style.backgroundColor = isSuccess ? '#28a745' : '#dc3545'; // Green for success, red for error

    $('.toast').toast('show'); // Use Bootstrap's jQuery function to show the toast
}


function saveSpeakerLabel(element, meetingId, speakerIndex) {
    var newLabel = element.innerText; // Get the updated label from the contenteditable element
    var originalLabel = element.getAttribute('data-original');
    var newLabel = element.innerText.trim(); // Trim to remove any extra white space
    if (newLabel === "") {
        showToast('Cannot update with an empty label.');
        element.innerText = element.getAttribute('data-original'); // Revert if new label is empty
        return;
    }
    $.ajax({
        url: '/update-speaker-label',
        type: 'POST',
        data: JSON.stringify({
            'meeting_id': meetingId,
            'speaker_index': speakerIndex,
            'new_label': newLabel
        }),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function(response) {
            showToast(response.message);
            //showToast('Speaker Labels updated successfully!');
        },
        error: function(xhr) {
            // showToast('There was an error updating the speaker label!');
            // showToast(xhr.responseJSON.error);
            element.innerText = element.getAttribute('data-original'); // Revert on error
        }
    });
}

function handleKeyDown(event, element, meetingId, speakerIndex) {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevents the default action (new line in the contenteditable element)
        saveSpeakerLabel(element, meetingId, speakerIndex);
    }
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}

function refreshTranscriptionData() {
    const meetingId = document.getElementById('meetingId').value;
    let meetingDate = document.getElementById('meetingDate').value;

    // Parse the date string into a Date object
    const date = new Date(meetingDate);

    if (!isNaN(date.getTime())) {
        // Format the date to YYYYMMDD_HHMMSS
        const formattedDate = formatDate(date);

        $.ajax({
            url: `/prev_meeting_info/${meetingId}/${formattedDate}`,
            type: 'GET',
            success: function(response) {
                $('.table-trans').html($(response).find('.table-trans').html());
                $('#meeting-summary').html($(response).find('#meeting-summary').html());
                $('#meeting-action').html($(response).find('#meeting-action').html());
            },
            error: function(xhr) {
                console.error('Failed to fetch updated transcription data:', xhr.statusText);
                // $('.toast-body').text('Failed to update transcription data.');
                // $('.toast').toast('show'); // Show toast notification for error
            }
        });
    } else {
        console.error('Invalid date provided:', meetingDate);
    }
}
setInterval(refreshTranscriptionData, 12000); // The interval can be adjusted as necessary
