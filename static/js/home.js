document.addEventListener('DOMContentLoaded', () => {
    // Adding smooth scroll to links in the navbar
    const links = document.querySelectorAll('nav ul li a');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.getAttribute('href').substring(1);
            document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // Adding login form validation
    const loginForm = document.querySelector("form");
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;

            // Basic client-side validation
            if (!username || !password) {
                e.preventDefault();  // Prevent form submission
                alert("Please fill in both fields.");
            } else {
                alert("Login successful!");
                // You can add actual login handling (AJAX or redirect) here.
            }
        });
    }
});
