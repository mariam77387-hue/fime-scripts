document.addEventListener("DOMContentLoaded", () => {

    const menuButton =
        document.getElementById("mobileMenuBtn");

    const mobileMenu =
        document.getElementById("mobileMenu");


    if (menuButton && mobileMenu) {

        menuButton.addEventListener("click", () => {

            mobileMenu.classList.toggle("open");

        });

    }


    /*
     * Close mobile menu when clicking a link
     */

    if (mobileMenu) {

        const links =
            mobileMenu.querySelectorAll("a");

        links.forEach(link => {

            link.addEventListener("click", () => {

                mobileMenu.classList.remove("open");

            });

        });

    }


    /*
     * Add current year automatically
     */

    document
        .querySelectorAll(".footer-bottom")
        .forEach(element => {

            element.innerHTML =
                element.innerHTML.replace(
                    "2026",
                    new Date().getFullYear()
                );

        });

});