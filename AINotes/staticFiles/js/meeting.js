function showToast(message) {  
  let toastElement = document.getElementById("toast");
  if (!toastElement) {
    // Dynamically create the toast element
    const toastContainer = document.querySelector(".toast-container");
    toastContainer.innerHTML = `
        <div
          id="toast"
          class="toast text-primary border-0"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
          data-autohide="true"
          data-delay="2000"
        >
          <div class="d-flex justify-content-between">
            <div class="toast-body">
              <i class="fa-solid fa-circle-exclamation text-danger"></i>
              <div class="ml-2"></div>
            </div>
            <button
              type="button"
              class="ml-2 mb-1 mr-3 d-flex mt-2 close"
              data-dismiss="toast"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
        </div>
      `;

    toastElement = document.getElementById("toast");
  }

  const toastBody = toastElement.querySelector(".toast-body > .ml-2");
  toastBody.textContent = message; // Set the toast message dynamically
  $(toastElement).toast("show"); // Use Bootstrap's jQuery function to show the toast
  $(toastElement).on('hidden.bs.toast', function () {
    $(this).remove();
  });
}

//////////////////////////////////////////////////////////// Handle the form submission for scheduled meetings//////////////////////////////////////////////////////////////////////////

document.addEventListener("DOMContentLoaded", function () {
  const createScheduledMeetingButton = document.getElementById(
    "createScheduledMeeting"
  );
  const scheduleMeetingForm = document.getElementById("scheduleMeetingForm");

  createScheduledMeetingButton.addEventListener("click", function (event) {
    event.preventDefault(); // Prevent the form from submitting normally

    createScheduledMeetingButton.disabled = true;


    // Use JavaScript to gather form data
    const formData = new FormData(scheduleMeetingForm);

    // Use Fetch API to send a POST request
    fetch(scheduleMeetingForm.action, {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Update the meeting ID and link fields in the scheduled section
          const sIdField = document.getElementById("S-ID");
          const sCopyTargetField = document.getElementById("S-copy-target");
          const scheduled_passCode =
            document.getElementById("scheduled_passCode");
          sIdField.value = data.meeting_id;
          sCopyTargetField.value = data.join_URL;
          scheduled_passCode.value = data.passcode;
          document.getElementById("labelScheduledID").style.display = "block"; // Assume similar label elements for scheduled
          document.getElementById("labelScheduledLink").style.display = "block";
          document.getElementById("labelScheduledPasscode").style.display =
            "block";
          if (data.calendar_link) {
              window.open(data.calendar_link, "_blank");
            }
          // showToast("Scheduled Meeting created successfully!");
          sessionStorage.setItem("meeting_id", data.meeting_id);
          sessionStorage.setItem("passcode", data.passcode);
          setTimeout(() => {
            createScheduledMeetingButton.disabled = false;
          }, 15000);
        } else {
          showToast(
            "Please ensure all required fields are completed. The Meeting Topic must be at least 4 characters long. Additionally, select a future time for the meeting",
            false
          )
          setTimeout(() => {
            createScheduledMeetingButton.disabled = false;
          }, 15000);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });
});

//////////////////////////////////////////////////////Handle the form submission for instant meetings/////////////////////////////////////////////////////////////////////////
document.addEventListener("DOMContentLoaded", function () {
  const createInstantMeetingButton = document.getElementById(
    "createInstantMeeting"
  );
  const instantMeetingForm = document.getElementById("instantMeetingForm");

  createInstantMeetingButton.addEventListener("click", function (event) {
    event.preventDefault(); // Prevent the form from submitting normally

    createInstantMeetingButton.disabled = true;

    // Use JavaScript to gather form data
    const formData = new FormData(instantMeetingForm);

    // Use Fetch API to send a POST request
    fetch(instantMeetingForm.action, {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Update the meeting ID and link fields in the instant section
          const instantIdField = document.getElementById("instant-ID");
          const instantCopyTargetField =
            document.getElementById("I-copy-target");
          const passCode = document.getElementById("passCode");
          instantIdField.value = data.meeting_id;
          instantCopyTargetField.value = data.join_URL;
          passCode.value = data.passcode;
          document.getElementById("labelInstantID").style.display = "block";
          document.getElementById("labelInstantLink").style.display = "block";
          document.getElementById("labelInstantPasscode").style.display =
            "block";
          if (data.calendar_link) {
              window.open(data.calendar_link, "_blank");
            }
          window.open(instantCopyTargetField.value, "_blank");
          // showToast("Instant Meeting created successfully!");
          sessionStorage.setItem("meeting_id", data.meeting_id);
          sessionStorage.setItem("passcode", data.passcode);
          console.log('going to disable button')
          
          setTimeout(() => {
            createInstantMeetingButton.disabled = false;
          }, 15000);
        } else {
          showToast(
            "Please ensure that all mandatory fields are filled. Meeting Topic should be greater than 3 characters. Please try again."
          )
          setTimeout(() => {
            createInstantMeetingButton.disabled = false;
          }, 15000);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });
});

//////////////////////////////////////////////////////////////////// Copy function for Instant Meeting /////////////////////////////////////////////////////////////////////////////
var copyButtonInstant = document.getElementById("I-copy-button");
copyButtonInstant.addEventListener("click", function () {
  // Use Clipboard API to copy joinUrl to clipboard
  var instantCopyTargetField = document.getElementById("I-copy-target");
  var joinUrlInstant = instantCopyTargetField.value;

  navigator.clipboard
    .writeText(joinUrlInstant)
    .then(function () {
      // Update the message element to indicate successful copy for the Instant Meeting section
      var copyMessageInstant = document.getElementById("copyMessageInstant");
      copyMessageInstant.textContent = "Meeting link copied to clipboard!";
      setTimeout(function () {
        copyMessageInstant.textContent = ""; // Clear the message after a few seconds
      }, 3000); // Clear after 3 seconds (adjust as needed)
    })
    .catch(function (err) {
      console.error("Unable to copy Instant Meeting URL to clipboard:", err);
    });
});
//////////////////////////////////////////////////////////////////// Copy function for Scheduled Meeting////////////////////////////////////////////////////////////////////////////////
var copyButtonScheduled = document.getElementById("S-copy-button");
copyButtonScheduled.addEventListener("click", function () {
  // Use Clipboard API to copy joinUrl to clipboard
  var scheduledCopyTargetField = document.getElementById("S-copy-target");
  var joinUrlScheduled = scheduledCopyTargetField.value;

  navigator.clipboard
    .writeText(joinUrlScheduled)
    .then(function () {
     
      // Update the message element to indicate successful copy
      var copyMessageScheduled = document.getElementById(
        "copyMessageScheduled"
      );
      copyMessageScheduled.textContent = "Meeting link copied to clipboard!";
      setTimeout(function () {
        copyMessageScheduled.textContent = ""; // Clear the message after a few seconds
      }, 3000); // Clear after 3 seconds (adjust as needed)
    })
    .catch(function (err) {
      console.error("Unable to copy Scheduled Meeting URL to clipboard:", err);
    });
});

/////////////////////////////////////////////////////////////////// Radio Button Click Event Handler //////////////////////////////////////////////////////////////////////////////////

document.addEventListener("DOMContentLoaded", function () {
  const radioButtons = document.getElementById("radio-buttons");
  const sections = document.querySelectorAll(".section");
  const instantSection = document.getElementById("instant-section");
  const scheduledSection = document.getElementById("scheduledMeeting");

  instantSection.style.display = "none";
  scheduledSection.style.display = "none";

  radioButtons.addEventListener("change", function (event) {
    if (event.target.value === "instant") {
      instantSection.style.display = "block";
      scheduledSection.style.display = "none";
    } else if (event.target.value === "scheduled") {
      instantSection.style.display = "none";
      scheduledSection.style.display = "block";
    }
  });
});
