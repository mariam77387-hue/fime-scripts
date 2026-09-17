let categories = [];
let scripts = [];

let editingScriptId = null;
let editingCategoryId = null;


/*
 * =========================================================
 * ELEMENTS
 * =========================================================
 */

const loginBox =
    document.getElementById("loginBox");

const dashboard =
    document.getElementById("dashboard");

const loginForm =
    document.getElementById("loginForm");

const loginMessage =
    document.getElementById("loginMessage");

const logoutButton =
    document.getElementById("logoutButton");

const categoryForm =
    document.getElementById("categoryForm");

const categoryName =
    document.getElementById("categoryName");

const categorySubmitButton =
    document.getElementById(
        "categorySubmitButton"
    );

const categoryCancelButton =
    document.getElementById(
        "categoryCancelButton"
    );

const categoryMessage =
    document.getElementById(
        "categoryMessage"
    );

const categoriesList =
    document.getElementById(
        "categoriesList"
    );

const categorySelect =
    document.getElementById(
        "category"
    );

const categoryCount =
    document.getElementById(
        "categoryCount"
    );

const scriptForm =
    document.getElementById(
        "scriptForm"
    );

const scriptFormTitle =
    document.getElementById(
        "scriptFormTitle"
    );

const scriptSubmitButton =
    document.getElementById(
        "scriptSubmitButton"
    );

const scriptCancelButton =
    document.getElementById(
        "scriptCancelButton"
    );

const scriptMessage =
    document.getElementById(
        "scriptMessage"
    );

const scriptsList =
    document.getElementById(
        "scriptsList"
    );

const scriptCount =
    document.getElementById(
        "scriptCount"
    );


/*
 * =========================================================
 * INIT
 * =========================================================
 */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        checkOwner();
    }
);


/*
 * =========================================================
 * OWNER SESSION
 * =========================================================
 */

async function checkOwner() {

    try {

        const response =
            await fetch(
                "/api/owner/me",
                {
                    credentials: "same-origin",
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            showLogin();
            return;
        }


        const data =
            await response.json();


        if (data.authenticated) {

            await showDashboard();

        } else {

            showLogin();

        }

    } catch (error) {

        console.error(
            "Owner check failed:",
            error
        );

        showLogin();
    }
}


/*
 * =========================================================
 * SHOW / HIDE
 * =========================================================
 */

async function showDashboard() {

    loginBox.hidden = true;
    dashboard.hidden = false;

    await Promise.all([
        loadCategories(),
        loadOwnerScripts()
    ]);
}


function showLogin() {

    loginBox.hidden = false;
    dashboard.hidden = true;
}


/*
 * =========================================================
 * LOGIN
 * =========================================================
 */

loginForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        setMessage(
            loginMessage,
            "جارٍ تسجيل الدخول...",
            ""
        );


        const username =
            document
                .getElementById(
                    "username"
                )
                .value
                .trim();


        const password =
            document
                .getElementById(
                    "password"
                )
                .value;


        try {

            const response =
                await fetch(
                    "/api/owner/login",
                    {
                        method: "POST",

                        credentials:
                            "same-origin",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body:
                            JSON.stringify({
                                username,
                                password
                            })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                setMessage(
                    loginMessage,
                    data.error ||
                        "فشل تسجيل الدخول.",
                    "error"
                );

                return;
            }


            loginForm.reset();

            setMessage(
                loginMessage,
                "",
                ""
            );


            await showDashboard();


        } catch (error) {

            console.error(error);

            setMessage(
                loginMessage,
                "حدث خطأ في الاتصال.",
                "error"
            );
        }
    }
);


/*
 * =========================================================
 * LOGOUT
 * =========================================================
 */

logoutButton.addEventListener(
    "click",
    async () => {

        try {

            await fetch(
                "/api/owner/logout",
                {
                    method: "POST",
                    credentials:
                        "same-origin"
                }
            );

        } catch (error) {

            console.error(error);

        } finally {

            editingScriptId = null;
            editingCategoryId = null;

            showLogin();

        }
    }
);


/*
 * =========================================================
 * CATEGORIES
 * =========================================================
 */

async function loadCategories() {

    try {

        const response =
            await fetch(
                "/api/categories",
                {
                    credentials:
                        "same-origin",
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            throw new Error(
                "Failed to load categories"
            );
        }


        categories =
            await response.json();


        renderCategories();
        renderCategorySelect();


    } catch (error) {

        console.error(error);

        categoriesList.textContent =
            "تعذر تحميل الأقسام.";

    }
}


/*
 * =========================================================
 * RENDER CATEGORIES
 * =========================================================
 */

function renderCategories() {

    categoryCount.textContent =
        categories.length;


    categoriesList.textContent = "";


    if (!categories.length) {

        categoriesList.innerHTML = `
            <div class="owner-empty">
                لا توجد أقسام حتى الآن.
            </div>
        `;

        return;
    }


    categories.forEach(category => {

        const item =
            document.createElement(
                "div"
            );

        item.className =
            "owner-category";


        if (
            editingCategoryId ===
            category.id
        ) {

            item.classList.add(
                "owner-editing"
            );
        }


        const info =
            document.createElement(
                "div"
            );

        info.className =
            "owner-item-info";


        const title =
            document.createElement(
                "strong"
            );

        title.textContent =
            category.name;


        info.appendChild(title);


        const actions =
            document.createElement(
                "div"
            );

        actions.className =
            "owner-item-actions";


        const editButton =
            document.createElement(
                "button"
            );

        editButton.type = "button";
        editButton.className =
            "btn btn-secondary";

        editButton.textContent =
            "تعديل";


        editButton.addEventListener(
            "click",
            () => {
                startCategoryEdit(
                    category
                );
            }
        );


        const deleteButton =
            document.createElement(
                "button"
            );

        deleteButton.type = "button";
        deleteButton.className =
            "btn btn-secondary owner-danger";

        deleteButton.textContent =
            "حذف";


        deleteButton.addEventListener(
            "click",
            () => {
                deleteCategory(
                    category.id,
                    category.name
                );
            }
        );


        actions.appendChild(
            editButton
        );

        actions.appendChild(
            deleteButton
        );


        item.appendChild(info);
        item.appendChild(actions);


        categoriesList.appendChild(item);

    });
}


/*
 * =========================================================
 * CATEGORY SELECT
 * =========================================================
 */

function renderCategorySelect() {

    const currentValue =
        categorySelect.value;


    categorySelect.innerHTML = "";


    const defaultOption =
        document.createElement(
            "option"
        );

    defaultOption.value = "";
    defaultOption.textContent =
        "اختر قسمًا";


    categorySelect.appendChild(
        defaultOption
    );


    categories.forEach(category => {

        const option =
            document.createElement(
                "option"
            );

        option.value =
            category.name;

        option.textContent =
            category.name;


        categorySelect.appendChild(
            option
        );
    });


    if (
        categories.some(
            category =>
                category.name ===
                currentValue
        )
    ) {

        categorySelect.value =
            currentValue;

    }
}


/*
 * =========================================================
 * CREATE / UPDATE CATEGORY
 * =========================================================
 */

categoryForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();


        const name =
            categoryName.value.trim();


        if (!name) {
            return;
        }


        categorySubmitButton.disabled =
            true;


        try {

            let response;


            if (editingCategoryId) {

                response =
                    await fetch(
                        `/api/owner/categories/${editingCategoryId}`,
                        {
                            method: "PUT",

                            credentials:
                                "same-origin",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    name
                                })
                        }
                    );

            } else {

                response =
                    await fetch(
                        "/api/owner/categories",
                        {
                            method: "POST",

                            credentials:
                                "same-origin",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    name
                                })
                        }
                    );
            }


            const data =
                await response.json();


            if (!response.ok) {

                setMessage(
                    categoryMessage,
                    data.error ||
                        "فشلت العملية.",
                    "error"
                );

                return;
            }


            setMessage(
                categoryMessage,
                editingCategoryId
                    ? "✅ تم تعديل القسم."
                    : "✅ تم إنشاء القسم.",
                "success"
            );


            resetCategoryForm();

            await loadCategories();


        } catch (error) {

            console.error(error);

            setMessage(
                categoryMessage,
                "حدث خطأ في الاتصال.",
                "error"
            );

        } finally {

            categorySubmitButton.disabled =
                false;

        }
    }
);


/*
 * =========================================================
 * START CATEGORY EDIT
 * =========================================================
 */

function startCategoryEdit(category) {

    editingCategoryId =
        category.id;


    categoryName.value =
        category.name;


    categorySubmitButton.textContent =
        "حفظ التعديل";


    categoryCancelButton.hidden =
        false;


    renderCategories();


    categoryName.focus();

    window.scrollTo({
        top:
            categoryForm
                .getBoundingClientRect()
                .top +
            window.scrollY -
            100,

        behavior: "smooth"
    });
}


/*
 * =========================================================
 * CANCEL CATEGORY EDIT
 * =========================================================
 */

categoryCancelButton.addEventListener(
    "click",
    () => {
        resetCategoryForm();
    }
);


function resetCategoryForm() {

    editingCategoryId =
        null;

    categoryForm.reset();

    categorySubmitButton.textContent =
        "إضافة القسم";

    categoryCancelButton.hidden =
        true;

    renderCategories();
}


/*
 * =========================================================
 * DELETE CATEGORY
 * =========================================================
 */

async function deleteCategory(
    id,
    name
) {

    const confirmed =
        window.confirm(
            `هل أنت متأكد من حذف قسم "${name}"؟`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/owner/categories/${id}`,
                {
                    method: "DELETE",
                    credentials:
                        "same-origin"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            setMessage(
                categoryMessage,
                data.error ||
                    "تعذر حذف القسم.",
                "error"
            );

            return;
        }


        setMessage(
            categoryMessage,
            "✅ تم حذف القسم.",
            "success"
        );


        await loadCategories();


    } catch (error) {

        console.error(error);

        setMessage(
            categoryMessage,
            "حدث خطأ أثناء حذف القسم.",
            "error"
        );
    }
}


/*
 * =========================================================
 * LOAD SCRIPTS
 * =========================================================
 */

async function loadOwnerScripts() {

    scriptsList.innerHTML = `
        <div class="owner-empty">
            جاري تحميل السكربتات...
        </div>
    `;


    try {

        const response =
            await fetch(
                "/api/scripts",
                {
                    credentials:
                        "same-origin",
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            if (
                response.status === 401
            ) {

                showLogin();

                return;
            }

            throw new Error(
                "Failed to load scripts"
            );
        }


        scripts =
            await response.json();


        renderScripts();


    } catch (error) {

        console.error(error);

        scriptsList.innerHTML = `
            <div class="owner-empty">
                تعذر تحميل السكربتات.
            </div>
        `;
    }
}


/*
 * =========================================================
 * RENDER SCRIPTS
 * =========================================================
 */

function renderScripts() {

    scriptCount.textContent =
        scripts.length;


    scriptsList.textContent = "";


    if (!scripts.length) {

        scriptsList.innerHTML = `
            <div class="owner-empty">
                لا توجد سكربتات حتى الآن.
            </div>
        `;

        return;
    }


    scripts.forEach(script => {

        const item =
            document.createElement(
                "div"
            );

        item.className =
            "owner-script";


        const info =
            document.createElement(
                "div"
            );

        info.className =
            "owner-item-info";


        const title =
            document.createElement(
                "strong"
            );

        title.textContent =
            script.title ||
            script.name ||
            "بدون اسم";


        const meta =
            document.createElement(
                "span"
            );

        const game =
            script.game ||
            "بدون لعبة";


        meta.textContent =
            `${script.category || "بدون قسم"} • ${game}`;


        info.appendChild(title);
        info.appendChild(meta);


        const actions =
            document.createElement(
                "div"
            );

        actions.className =
            "owner-item-actions";


        const editButton =
            document.createElement(
                "button"
            );

        editButton.type = "button";
        editButton.className =
            "btn btn-secondary";

        editButton.textContent =
            "تعديل";


        editButton.addEventListener(
            "click",
            () => {
                startScriptEdit(
                    script
                );
            }
        );


        const deleteButton =
            document.createElement(
                "button"
            );

        deleteButton.type = "button";
        deleteButton.className =
            "btn btn-secondary owner-danger";

        deleteButton.textContent =
            "حذف";


        deleteButton.addEventListener(
            "click",
            () => {
                deleteScript(
                    script.id,
                    script.title
                );
            }
        );


        actions.appendChild(
            editButton
        );

        actions.appendChild(
            deleteButton
        );


        item.appendChild(info);
        item.appendChild(actions);


        scriptsList.appendChild(item);

    });
}


/*
 * =========================================================
 * CREATE / UPDATE SCRIPT
 * =========================================================
 */

scriptForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();


        const payload = {

            title:
                document
                    .getElementById("title")
                    .value
                    .trim(),

            description:
                document
                    .getElementById("description")
                    .value
                    .trim(),

            game:
                document
                    .getElementById("game")
                    .value
                    .trim(),

            type:
                document
                    .getElementById("type")
                    .value
                    .trim() ||
                "Script",

            category:
                categorySelect.value,

            tags:
                document
                    .getElementById("tags")
                    .value
                    .split(",")
                    .map(tag =>
                        tag.trim()
                    )
                    .filter(Boolean),

            image:
                document
                    .getElementById("image")
                    .value
                    .trim(),

            code:
                document
                    .getElementById("code")
                    .value,

            featured:
                document
                    .getElementById("featured")
                    .checked
        };


        if (!payload.category) {

            setMessage(
                scriptMessage,
                "اختر قسمًا أولًا.",
                "error"
            );

            return;
        }


        scriptSubmitButton.disabled =
            true;


        try {

            let response;


            if (editingScriptId) {

                response =
                    await fetch(
                        `/api/owner/scripts/${editingScriptId}`,
                        {
                            method: "PUT",

                            credentials:
                                "same-origin",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    payload
                                )
                        }
                    );

            } else {

                response =
                    await fetch(
                        "/api/owner/scripts",
                        {
                            method: "POST",

                            credentials:
                                "same-origin",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    payload
                                )
                        }
                    );
            }


            const data =
                await response.json();


            if (!response.ok) {

                if (
                    response.status ===
                    401
                ) {

                    showLogin();

                    return;
                }


                setMessage(
                    scriptMessage,
                    data.error ||
                        "فشلت العملية.",
                    "error"
                );

                return;
            }


            setMessage(
                scriptMessage,
                editingScriptId
                    ? "✅ تم تعديل السكربت."
                    : "✅ تم نشر السكربت.",
                "success"
            );


            resetScriptForm();

            await loadOwnerScripts();


        } catch (error) {

            console.error(error);

            setMessage(
                scriptMessage,
                "حدث خطأ في الاتصال.",
                "error"
            );

        } finally {

            scriptSubmitButton.disabled =
                false;

        }
    }
);


/*
 * =========================================================
 * START SCRIPT EDIT
 * =========================================================
 */

function startScriptEdit(script) {

    editingScriptId =
        script.id;


    document.getElementById(
        "title"
    ).value =
        script.title ||
        script.name ||
        "";


    document.getElementById(
        "description"
    ).value =
        script.description ||
        "";


    document.getElementById(
        "game"
    ).value =
        script.game ||
        "";


    document.getElementById(
        "type"
    ).value =
        script.type ||
        "Script";


    document.getElementById(
        "tags"
    ).value =
        Array.isArray(script.tags)
            ? script.tags.join(", ")
            : "";


    document.getElementById(
        "image"
    ).value =
        script.image ||
        "";


    document.getElementById(
        "code"
    ).value =
        script.code ||
        "";


    document.getElementById(
        "featured"
    ).checked =
        Boolean(
            script.featured
        );


    categorySelect.value =
        script.category ||
        "";


    scriptFormTitle.textContent =
        "✏️ تعديل السكربت";


    scriptSubmitButton.textContent =
        "حفظ التعديلات";


    scriptCancelButton.hidden =
        false;


    renderScripts();


    scriptForm.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/*
 * =========================================================
 * CANCEL SCRIPT EDIT
 * =========================================================
 */

scriptCancelButton.addEventListener(
    "click",
    () => {
        resetScriptForm();
    }
);


function resetScriptForm() {

    editingScriptId =
        null;


    scriptForm.reset();


    document.getElementById(
        "type"
    ).value =
        "Script";


    scriptFormTitle.textContent =
        "➕ إضافة سكربت";


    scriptSubmitButton.textContent =
        "نشر السكربت";


    scriptCancelButton.hidden =
        true;


    renderScripts();
}


/*
 * =========================================================
 * DELETE SCRIPT
 * =========================================================
 */

async function deleteScript(
    id,
    title
) {

    const confirmed =
        window.confirm(
            `هل أنت متأكد من حذف "${title || "هذا السكربت"}"؟`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/owner/scripts/${id}`,
                {
                    method: "DELETE",

                    credentials:
                        "same-origin"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status ===
                401
            ) {

                showLogin();

                return;
            }


            setMessage(
                scriptMessage,
                data.error ||
                    "فشل حذف السكربت.",
                "error"
            );

            return;
        }


        setMessage(
            scriptMessage,
            "✅ تم حذف السكربت.",
            "success"
        );


        if (
            String(editingScriptId) ===
            String(id)
        ) {

            resetScriptForm();

        }


        await loadOwnerScripts();


    } catch (error) {

        console.error(error);

        setMessage(
            scriptMessage,
            "حدث خطأ أثناء حذف السكربت.",
            "error"
        );
    }
}


/*
 * =========================================================
 * MESSAGE
 * =========================================================
 */

function setMessage(
    element,
    message,
    type
) {

    element.textContent =
        message;


    element.classList.remove(
        "error",
        "success"
    );


    if (type) {
        element.classList.add(type);
    }
}