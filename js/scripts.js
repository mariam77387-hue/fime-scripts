let allScripts = [];
let currentCategory = "all";


document.addEventListener("DOMContentLoaded", async () => {

    const scriptsGrid =
        document.getElementById("scriptsGrid");

    const hacksGrid =
        document.getElementById("hacksGrid");


    if (!scriptsGrid && !hacksGrid) {
        return;
    }


    try {

        const response =
            await fetch("data/scripts.json");

        if (!response.ok) {
            throw new Error("Failed to load scripts");
        }

        allScripts =
            await response.json();


        if (scriptsGrid) {

            setupScriptsPage();

        }


        if (hacksGrid) {

            setupHacksPage();

        }


    } catch (error) {

        console.error(error);

        if (scriptsGrid) {

            scriptsGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">!</div>
                    <h3>Unable to load scripts</h3>
                    <p>Please try again later.</p>
                </div>
            `;

        }

    }

});


/*
 * SCRIPTS PAGE
 */

function setupScriptsPage() {

    const searchInput =
        document.getElementById("scriptSearch");

    const filterContainer =
        document.getElementById("categoryFilters");


    createCategoryFilters(filterContainer);

    renderScripts(allScripts);


    if (searchInput) {

        searchInput.addEventListener(
            "input",
            () => {

                renderScripts(
                    getFilteredScripts(
                        searchInput.value
                    )
                );

            }
        );

    }

}


/*
 * HACKS PAGE
 */

function setupHacksPage() {

    const hacks =
        allScripts.filter(
            script =>
                script.type?.toLowerCase() === "hack"
                ||
                script.category?.toLowerCase() === "hacks"
        );


    const grid =
        document.getElementById("hacksGrid");

    const empty =
        document.getElementById("hacksEmpty");


    if (!hacks.length) {

        if (grid) {
            grid.innerHTML = "";
        }

        if (empty) {
            empty.style.display = "block";
        }

        return;
    }


    if (empty) {
        empty.style.display = "none";
    }


    renderScripts(hacks, grid);

}


/*
 * CATEGORY FILTERS
 */

function createCategoryFilters(container) {

    if (!container) {
        return;
    }


    const categories =
        [
            ...new Set(
                allScripts
                    .map(script => script.category)
                    .filter(Boolean)
            )
        ];


    categories.forEach(category => {

        const button =
            document.createElement("button");

        button.className =
            "filter-btn";

        button.dataset.category =
            category;

        button.textContent =
            category;


        button.addEventListener(
            "click",
            () => {

                currentCategory =
                    category;

                container
                    .querySelectorAll(".filter-btn")
                    .forEach(btn =>
                        btn.classList.remove("active")
                    );

                button.classList.add("active");


                const search =
                    document.getElementById(
                        "scriptSearch"
                    );


                renderScripts(
                    getFilteredScripts(
                        search?.value || ""
                    )
                );

            }
        );


        container.appendChild(button);

    });


    const allButton =
        container.querySelector(
            '[data-category="all"]'
        );


    if (allButton) {

        allButton.addEventListener(
            "click",
            () => {

                currentCategory = "all";

                container
                    .querySelectorAll(".filter-btn")
                    .forEach(btn =>
                        btn.classList.remove("active")
                    );

                allButton.classList.add("active");


                const search =
                    document.getElementById(
                        "scriptSearch"
                    );


                renderScripts(
                    getFilteredScripts(
                        search?.value || ""
                    )
                );

            }
        );

    }

}


/*
 * FILTER
 */

function getFilteredScripts(searchText) {

    const query =
        searchText
            .trim()
            .toLowerCase();


    return allScripts.filter(script => {

        const matchesCategory =
            currentCategory === "all"
            ||
            script.category === currentCategory;


        const searchableText = [

            script.name,
            script.description,
            script.category,
            script.type,
            ...(script.tags || [])

        ]
            .join(" ")
            .toLowerCase();


        const matchesSearch =
            !query
            ||
            searchableText.includes(query);


        return matchesCategory &&
               matchesSearch;

    });

}


/*
 * RENDER
 */

function renderScripts(
    scripts,
    target = document.getElementById("scriptsGrid")
) {

    if (!target) {
        return;
    }


    const emptyState =
        document.getElementById("emptyState");


    if (!scripts.length) {

        target.innerHTML = "";

        if (emptyState) {
            emptyState.style.display =
                "block";
        }

        return;
    }


    if (emptyState) {
        emptyState.style.display =
            "none";
    }


    target.innerHTML =
        scripts
            .map(createScriptCard)
            .join("");

}


/*
 * CARD
 */

function createScriptCard(script) {

    const tags =
        (script.tags || [])
            .slice(0, 4)
            .map(
                tag =>
                    `<span class="tag">
                        ${escapeHTML(tag)}
                    </span>`
            )
            .join("");


    return `
        <article class="script-card">

            <div class="script-card-top">

                <div class="script-icon">
                    ${script.type?.toLowerCase() === "hack"
                        ? "🧩"
                        : "📜"}
                </div>

                <span class="script-category">
                    ${escapeHTML(
                        script.category || "Other"
                    )}
                </span>

            </div>


            <h3>
                ${escapeHTML(script.name)}
            </h3>


            <p>
                ${escapeHTML(
                    script.description || ""
                )}
            </p>


            <div class="script-tags">
                ${tags}
            </div>


            <div class="script-card-bottom">

                <a
                    class="card-btn primary"
                    href="script.html?id=${encodeURIComponent(script.id)}">

                    View

                </a>

                <button
                    class="card-btn"
                    onclick="copyScript('${escapeAttribute(script.id)}')">

                    Copy

                </button>

            </div>

        </article>
    `;

}


/*
 * COPY DIRECTLY FROM CARD
 */

async function copyScript(id) {

    const script =
        allScripts.find(
            item => item.id === id
        );


    if (!script) {
        return;
    }


    try {

        await navigator.clipboard.writeText(
            script.code
        );


        showToast(
            "Script copied!"
        );


    } catch (error) {

        console.error(error);

        showToast(
            "Copy failed."
        );

    }

}


/*
 * TOAST
 */

function showToast(message) {

    let toast =
        document.getElementById(
            "fimeToast"
        );


    if (!toast) {

        toast =
            document.createElement("div");

        toast.id =
            "fimeToast";

        toast.style.position =
            "fixed";

        toast.style.bottom =
            "25px";

        toast.style.left =
            "50%";

        toast.style.transform =
            "translateX(-50%)";

        toast.style.zIndex =
            "9999";

        toast.style.padding =
            "12px 18px";

        toast.style.borderRadius =
            "10px";

        toast.style.background =
            "#161923";

        toast.style.border =
            "1px solid rgba(255,255,255,.1)";

        toast.style.color =
            "white";

        toast.style.fontSize =
            "14px";

        document.body.appendChild(toast);

    }


    toast.textContent =
        message;


    toast.style.opacity =
        "1";


    clearTimeout(
        window.fimeToastTimeout
    );


    window.fimeToastTimeout =
        setTimeout(
            () => {

                toast.style.opacity =
                    "0";

            },
            1800
        );

}


/*
 * SECURITY / HTML HELPERS
 */

function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


function escapeAttribute(value) {

    return String(value)
        .replaceAll("\\", "\\\\")
        .replaceAll("'", "\\'");

}