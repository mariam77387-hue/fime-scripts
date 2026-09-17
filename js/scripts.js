let allScripts = [];
let currentCategory = "all";

document.addEventListener("DOMContentLoaded", async () => {
    const scriptsGrid = document.getElementById("scriptsGrid");
    const hacksGrid = document.getElementById("hacksGrid");

    if (!scriptsGrid && !hacksGrid) {
        return;
    }

    try {
        const response = await fetch("data/scripts.json", {
            cache: "no-cache"
        });

        if (!response.ok) {
            throw new Error("Failed to load scripts");
        }

        const data = await response.json();

        if (!Array.isArray(data)) {
            throw new Error("Invalid scripts.json format");
        }

        allScripts = data.filter(isValidScript);

        if (scriptsGrid) {
            setupScriptsPage();
        }

        if (hacksGrid) {
            setupHacksPage();
        }

    } catch (error) {
        console.error("Fime Scripts error:", error);

        if (scriptsGrid) {
            showLoadError(scriptsGrid);
        }

        if (hacksGrid) {
            showLoadError(hacksGrid);
        }
    }
});


/*
 * VALIDATE SCRIPT
 */

function isValidScript(script) {
    return (
        script &&
        typeof script.id === "string" &&
        typeof script.name === "string" &&
        typeof script.description === "string" &&
        typeof script.code === "string"
    );
}


/*
 * SCRIPTS PAGE
 */

function setupScriptsPage() {
    const searchInput =
        document.getElementById("scriptSearch");

    const filterContainer =
        document.getElementById("categoryFilters");

    createCategoryFilters(filterContainer);

    renderScripts(
        getFilteredScripts(
            searchInput?.value || ""
        )
    );

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            renderScripts(
                getFilteredScripts(
                    searchInput.value
                )
            );
        });
    }
}


/*
 * HACKS PAGE
 */

function setupHacksPage() {
    const hacks =
        allScripts.filter(script => {
            const type =
                String(script.type || "")
                    .trim()
                    .toLowerCase();

            const category =
                String(script.category || "")
                    .trim()
                    .toLowerCase();

            return (
                type === "hack" ||
                category === "hacks"
            );
        });

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

    container.innerHTML = "";

    const allButton =
        document.createElement("button");

    allButton.className =
        "filter-btn active";

    allButton.dataset.category = "all";

    allButton.textContent = "الكل";

    allButton.addEventListener("click", () => {
        currentCategory = "all";

        setActiveFilter(
            container,
            allButton
        );

        const search =
            document.getElementById(
                "scriptSearch"
            );

        renderScripts(
            getFilteredScripts(
                search?.value || ""
            )
        );
    });

    container.appendChild(allButton);


    const categories = [
        ...new Set(
            allScripts
                .map(script =>
                    String(
                        script.category || ""
                    ).trim()
                )
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

        button.addEventListener("click", () => {
            currentCategory =
                category;

            setActiveFilter(
                container,
                button
            );

            const search =
                document.getElementById(
                    "scriptSearch"
                );

            renderScripts(
                getFilteredScripts(
                    search?.value || ""
                )
            );
        });

        container.appendChild(button);
    });
}


function setActiveFilter(
    container,
    activeButton
) {
    container
        .querySelectorAll(".filter-btn")
        .forEach(button => {
            button.classList.remove("active");
        });

    activeButton.classList.add("active");
}


/*
 * FILTER
 */

function getFilteredScripts(searchText) {
    const query =
        String(searchText || "")
            .trim()
            .toLowerCase();

    return allScripts.filter(script => {
        const matchesCategory =
            currentCategory === "all" ||
            script.category === currentCategory;

        const searchableText = [
            script.name,
            script.description,
            script.category,
            script.type,
            ...(Array.isArray(script.tags)
                ? script.tags
                : [])
        ]
            .join(" ")
            .toLowerCase();

        const matchesSearch =
            !query ||
            searchableText.includes(query);

        return (
            matchesCategory &&
            matchesSearch
        );
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
            emptyState.style.display = "block";
        }

        return;
    }

    if (emptyState) {
        emptyState.style.display = "none";
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
        (
            Array.isArray(script.tags)
                ? script.tags
                : []
        )
            .slice(0, 4)
            .map(tag => {
                return `
                    <span class="tag">
                        ${escapeHTML(tag)}
                    </span>
                `;
            })
            .join("");


    const isHack =
        String(script.type || "")
            .toLowerCase() === "hack";


    return `
        <article class="script-card">

            <div class="script-card-top">

                <div class="script-icon">
                    ${isHack ? "🧩" : "📜"}
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
                    href="script.html?id=${encodeURIComponent(
                        script.id
                    )}"
                >
                    عرض
                </a>


                <button
                    class="card-btn"
                    type="button"
                    data-copy-script="${escapeHTML(
                        script.id
                    )}"
                >
                    نسخ
                </button>

            </div>

        </article>
    `;
}


/*
 * COPY BUTTON
 *
 * بدل onclick داخل HTML،
 * نستخدم event delegation.
 */

document.addEventListener("click", event => {
    const button =
        event.target.closest(
            "[data-copy-script]"
        );

    if (!button) {
        return;
    }

    const id =
        button.dataset.copyScript;

    copyScript(id);
});


async function copyScript(id) {
    const script =
        allScripts.find(
            item => item.id === id
        );

    if (!script) {
        showToast("السكربت غير موجود.");
        return;
    }

    try {
        await navigator.clipboard.writeText(
            script.code
        );

        showToast(
            "تم نسخ السكربت ✓"
        );

    } catch (error) {
        console.error(error);

        showToast(
            "تعذر نسخ السكربت."
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

        Object.assign(
            toast.style,
            {
                position: "fixed",
                bottom: "25px",
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: "9999",
                padding: "12px 18px",
                borderRadius: "10px",
                background: "#161923",
                border: "1px solid rgba(255,255,255,.1)",
                color: "white",
                fontSize: "14px",
                opacity: "0",
                transition: "opacity .2s ease"
            }
        );

        document.body.appendChild(toast);
    }

    toast.textContent = message;

    toast.style.opacity = "1";

    clearTimeout(
        window.fimeToastTimeout
    );

    window.fimeToastTimeout =
        setTimeout(() => {
            toast.style.opacity = "0";
        }, 1800);
}


/*
 * ERROR
 */

function showLoadError(target) {
    target.innerHTML = `
        <div class="empty-state">

            <div class="empty-icon">
                !
            </div>

            <h3>
                تعذر تحميل السكربتات
            </h3>

            <p>
                حاول تحديث الصفحة مرة أخرى.
            </p>

        </div>
    `;
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