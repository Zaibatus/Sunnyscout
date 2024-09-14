document.addEventListener('DOMContentLoaded', function() {
    // Form handling
    const startSearchBtn = document.getElementById('start-search');
    const homePage = document.querySelector('.home-page');
    const typeformContainer = document.querySelector('.typeform-container');
    const progressBar = document.querySelector('.progress');
    const questions = document.querySelectorAll('.question');
    const totalQuestions = questions.length;
    const exploreButton = document.getElementById('explore-button');
    const searchForm = document.getElementById('search-form');
    const errorMessage = document.getElementById('error-message');
    const locationInput = document.getElementById('current-location');
    const dateRangeInput = document.getElementById('date-range');
    const dateErrorMessage = document.getElementById('date-error-message');

    // Function to show a specific question
    function showQuestion(questionIndex) {
        questions.forEach((q, index) => {
            if (index === questionIndex) {
                q.classList.add('active');
            } else {
                q.classList.remove('active');
            }
        });
        updateProgress(questionIndex + 1);
    }

    // Function to update progress bar
    function updateProgress(currentQuestion) {
        const progress = (currentQuestion / totalQuestions) * 100;
        progressBar.style.width = `${progress}%`;
    }

    // Start search button click handler
    startSearchBtn.addEventListener('click', function() {
        homePage.classList.remove('active');
        typeformContainer.classList.add('active');
        updateProgress(1);
    });

    // Function to validate location input before moving to the next question
    function validateLocationInput() {
        const locationValue = locationInput.value.trim();
        if (locationValue === "") {
            errorMessage.style.display = 'block';  // Show error message
            return false;
        } else {
            errorMessage.style.display = 'none';  // Hide error message
            return true;
        }
    }

    // Function to validate date range input before moving to the next question
    function validateDateInput() {
        const dateValue = dateRangeInput.value.trim();
        if (dateValue === "") {
            dateErrorMessage.style.display = 'block';  // Show error message
            return false;
        } else {
            dateErrorMessage.style.display = 'none';  // Hide error message
            return true;
        }
    }

    // Next button click handlers
    document.querySelectorAll('.next-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const currentQuestion = this.closest('.question');
            const nextQuestion = currentQuestion.nextElementSibling;

            // If this is the location question, validate the input
            if (currentQuestion.id === 'location-question') {
                if (!validateLocationInput()) {
                    return;  // Prevent proceeding if validation fails
                }
            }

            // If this is the date question, validate the input
            if (currentQuestion.id === 'date-question') {
                if (!validateDateInput()) {
                    return;  // Prevent proceeding if validation fails
                }
            }

            if (nextQuestion) {
                currentQuestion.classList.remove('active');
                nextQuestion.classList.add('active');
                updateProgress(parseInt(nextQuestion.dataset.question));
            }
        });
    });

    // Back button click handlers
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const currentQuestion = this.closest('.question');
            const previousQuestion = currentQuestion.previousElementSibling;
            if (previousQuestion) {
                currentQuestion.classList.remove('active');
                previousQuestion.classList.add('active');
                updateProgress(parseInt(previousQuestion.dataset.question));
            }
        });
    });

    // Explore button click handler
    exploreButton.addEventListener('click', function(e) {
        e.preventDefault();
        if (searchForm.checkValidity()) {
            const dateRange = document.getElementById('date-range').value.split(' to ');
            const startDate = dateRange[0];
            const endDate = dateRange[1] || dateRange[0];
            const currentLocation = locationInput.value;
            const preferences = {
                island: document.querySelector('input[name="island"]:checked').value,
                capital: document.querySelector('input[name="capital"]:checked').value,
                eu: document.querySelector('input[name="eu"]:checked').value,
                schengen: document.querySelector('input[name="schengen"]:checked').value
            };
            const distance = document.getElementById('distance').value;
            const populationMin = document.getElementById('population-min').value;
            const populationMax = document.getElementById('population-max').value;

            const queryParams = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                current_location: currentLocation,
                preferences: JSON.stringify(preferences),
                distance: distance,
                population_min: populationMin,
                population_max: populationMax
            });

            window.location.href = `/results?${queryParams.toString()}`;
        } else {
            searchForm.reportValidity();
        }
    });

    // Date range picker initialization
    const today = new Date();
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 15);

    flatpickr(dateRangeInput, {
        mode: "range",
        dateFormat: "Y-m-d",
        minDate: "today",
        maxDate: maxDate,
        defaultDate: [today, new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)],
        onChange: function(selectedDates, dateStr, instance) {
            if (selectedDates.length === 2) {
                const startDate = selectedDates[0];
                const endDate = selectedDates[1];
                const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
                if (daysDiff > 15) {
                    instance.setDate([startDate, new Date(startDate.getTime() + 14 * 24 * 60 * 60 * 1000)]);
                }
            }
        }
    });

    // City autocomplete
    const citiesList = document.getElementById('cities-list');

    fetch('/get_cities')
        .then(response => response.json())
        .then(cities => {
            cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                citiesList.appendChild(option);
            });
        });

    locationInput.addEventListener('input', function() {
        const value = this.value.toLowerCase();
        const options = citiesList.getElementsByTagName('option');
        for (let i = 0; i < options.length; i++) {
            const optionValue = options[i].value.toLowerCase();
            if (optionValue.startsWith(value)) {
                options[i].style.display = '';
            } else {
                options[i].style.display = 'none';
            }
        }
    });

    // Check for #search-form anchor in URL
    if (window.location.hash === '#search-form') {
        homePage.classList.remove('active');
        typeformContainer.classList.add('active');
        showQuestion(0);
        document.getElementById('search-form').scrollIntoView();
    }

    // Distance slider functionality
    const distanceSlider = document.getElementById('distance');
    const distanceValue = document.getElementById('distance-value');

    distanceSlider.addEventListener('input', function() {
        if (this.value == 5000) {
            distanceValue.textContent = 'Any distance';
        } else {
            distanceValue.textContent = `${this.value} km`;
        }
    });

    // Update the distance value when the page loads
    window.addEventListener('load', function() {
        if (distanceSlider.value == 5000) {
            distanceValue.textContent = 'Any distance';
        } else {
            distanceValue.textContent = `${distanceSlider.value} km`;
        }
    });
});
