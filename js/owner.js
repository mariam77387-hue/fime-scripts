(() => {
    "use strict";


    /* =========================================================
       Fime Owner Dashboard
       ========================================================= */


    const state = {
        categories: [],
        scripts: [],
        editingScriptId: null
    };


    const elements = {
        loginBox: document.getElementById("loginBox"),
        dashboard: document.getElementById("dashboard"),

        loginForm: document.getElementById("loginForm"),
        ownerUsername: document.getElementById("ownerUsername"),
        ownerPassword: document.getElementById("ownerPassword"),
        loginMessage: document.getElementById("loginMessage"),

        logoutButton: document.getElementById("logoutButton"),

        categoryForm: document.getElementById("categoryForm"),
        categoryName: document.getElementById("categoryName"),
        categoryMessage: document.getElementById("categoryMessage"),
        categoryList: document.getElementById("categoryList"),

        scriptForm: document.getElementById("scriptForm"),
        scriptTitle: document.getElementById("scriptTitle"),
        scriptDescription: document.getElementById("scriptDescription"),
        scriptGame: document.getElementById("scriptGame"),
        scriptCode: document.getElementById("scriptCode"),
        scriptImage: document.getElementById("scriptImage"),
        scriptFeatured: document.getElementById("scriptFeatured"),
        category: document.getElementById("category"),

        scriptMessage: document.getElementById("scriptMessage"),

        scriptsList: document.getElementById("scriptsList"),

        editingScriptId: document.getElementById("editingScriptId"),
        editBadge: document.getElementById("editBadge"),
        publishButton: document.getElementById("publishButton"),
        cancelEditButton: document.getElementById("cancelEditButton")
    };


    /* =========================================================
       API
       ========================================================= */

    async function apiFetch(
        url,
        options = {}
    ) {

        const response = await fetch(
            url,
            {
                ...options,

                credentials: "same-origin",

                cache: "no-store",

                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                }
            }
        );


        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }


        if (!response.ok) {

            const error =
                data?.error ||
                data?.message ||
                `HTTP ${response.status}`;

            const exception =
                new Error(error);

            exception.status =
                response.status;

            throw exception;
        }


        return data;
    }


    /* =========================================================
       Messages
       ========================================================= */

    function showMessage(
        element,
        message,
        type = ""
    ) {

        if (!element) return;

        element.textContent =
            message || "";

        element.className =
            `message ${type}`.trim();
    }


    function clearMessage(element) {

        if (!element) return;

        element.textContent = "";
        element.className = "message";
    }


    /* =========================================================
       Authentication
       ========================================================= */

    async function checkSession() {

        try {

            const data =
                await apiFetch(
                    "/api/owner/me"
                );


            if (data.authenticated) {

                showDashboard();

                await loadDashboard();

            } else {

                showLogin();

            }

        } catch (error) {

            console.error(
                "Session check failed:",
                error
            );

            showLogin();
        }
    }


    function showLogin() {

        if (elements.loginBox) {
            elements.loginBox.style.display =
                "block";
        }

        if (elements.dashboard) {
            elements.dashboard.style.display =
                "none";
        }
    }


    function showDashboard() {

        if (elements.loginBox) {
            elements.loginBox.style.display =
                "none";
        }

        if (elements.dashboard) {
            elements.dashboard.style.display =
                "block";
        }
    }


    /* =========================================================
       Login
       ========================================================= */

    async function login(event) {

        event.preventDefault();

        clearMessage(
            elements.loginMessage
        );


        const username =
            elements.ownerUsername
                ?.value
                ?.trim() || "";


        const password =
            elements.ownerPassword
                ?.value || "";


        if (!username) {

            showMessage(
                elements.loginMessage,
                "اكتب اسم المستخدم.",
                "error"
            );

            return;
        }


        if (!password) {

            showMessage(
                elements.loginMessage,
                "اكتب كلمة المرور.",
                "error"
            );

            return;
        }


        const button =
            elements.loginForm
                ?.querySelector(
                    'button[type="submit"]'
                );


        const originalText =
            button?.textContent ||
            "تسجيل الدخول";


        if (button) {
            button.disabled = true;
            button.textContent =
                "جاري تسجيل الدخول...";
        }


        try {

            await apiFetch(
                "/api/owner/login",
                {
                    method: "POST",

                    body: JSON.stringify({
                        username,
                        password
                    })
                }
            );


            elements.ownerPassword.value =
                "";


            showMessage(
                elements.loginMessage,
                "تم تسجيل الدخول بنجاح.",
                "success"
            );


            showDashboard();


            await loadDashboard();


        } catch (error) {

            console.error(
                "Login failed:",
                error
            );


            showMessage(
                elements.loginMessage,
                error.message ||
                "بيانات الدخول غير صحيحة.",
                "error"
            );

        } finally {

            if (button) {

                button.disabled = false;

                button.textContent =
                    originalText;
            }
        }
    }


    /* =========================================================
       Logout
       ========================================================= */

    async function logout() {

        try {

            await apiFetch(
                "/api/owner/logout",
                {
                    method: "POST"
                }
            );

        } catch (error) {

            console.error(
                "Logout error:",
                error
            );

        } finally {

            state.categories = [];
            state.scripts = [];
            state.editingScriptId = null;

            resetScriptForm();

            showLogin();

            showMessage(
                elements.loginMessage,
                "تم تسجيل الخروج.",
                "success"
            );
        }
    }


    /* =========================================================
       Load Dashboard
       ========================================================= */

    async function loadDashboard() {

        try {

            await Promise.all([
                loadCategories(),
                loadScripts()
            ]);

        } catch (error) {

            console.error(
                "Dashboard load error:",
                error
            );
        }
    }


    /* =========================================================
       Categories
       ========================================================= */

    async function loadCategories() {

        const data =
            await apiFetch(
                "/api/categories"
            );


        state.categories =
            Array.isArray(data)
                ? data
                : [];


        renderCategorySelect();

        renderCategoryList();
    }


    function renderCategorySelect() {

        if (!elements.category) {
            return;
        }


        const currentValue =
            elements.category.value;


        elements.category.innerHTML = "";


        /*
         * هذا الخيار موجود دائماً.
         *
         * وبالتالي التصنيف ليس مطلوباً.
         */

        const emptyOption =
            document.createElement("option");

        emptyOption.value = "";

        emptyOption.textContent =
            "بدون تصنيف";

        elements.category.appendChild(
            emptyOption
        );


        for (
            const category
            of state.categories
        ) {

            if (!category?.name) {
                continue;
            }


            const option =
                document.createElement("option");

            option.value =
                category.name;

            option.textContent =
                category.name;

            elements.category.appendChild(
                option
            );
        }


        /*
         * نحاول الاحتفاظ بالاختيار السابق
         */

        const exists =
            Array.from(
                elements.category.options
            ).some(
                option =>
                    option.value === currentValue
            );


        elements.category.value =
            exists
                ? currentValue
                : "";
    }


    function renderCategoryList() {

        if (!elements.categoryList) {
            return;
        }


        elements.categoryList.innerHTML =
            "";


        if (
            state.categories.length === 0
        ) {

            const empty =
                document.createElement("div");

            empty.textContent =
                "لا توجد تصنيفات حالياً.";

            empty.style.opacity =
                ".6";

            elements.categoryList.appendChild(
                empty
            );

            return;
        }


        for (
            const category
            of state.categories
        ) {

            const item =
                document.createElement("div");

            item.className =
                "category-item";


            const nameWrapper =
                document.createElement("div");

            nameWrapper.className =
                "category-name";


            const name =
                document.createElement("span");

            name.textContent =
                category.name;


            nameWrapper.appendChild(
                name
            );


            if (category.is_default) {

                const badge =
                    document.createElement("span");

                badge.className =
                    "category-default";

                badge.textContent =
                    "أساسي";

                nameWrapper.appendChild(
                    badge
                );
            }


            item.appendChild(
                nameWrapper
            );


            /*
             * التصنيفات الأساسية لا نحذفها.
             */

            if (!category.is_default) {

                const deleteButton =
                    document.createElement("button");

                deleteButton.type =
                    "button";

                deleteButton.className =
                    "owner-button owner-danger";

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


                item.appendChild(
                    deleteButton
                );
            }


            elements.categoryList.appendChild(
                item
            );
        }
    }


    /* =========================================================
       Create Category
       ========================================================= */

    async function createCategory(event) {

        event.preventDefault();

        clearMessage(
            elements.categoryMessage
        );


        const name =
            elements.categoryName
                ?.value
                ?.trim() || "";


        if (!name) {

            showMessage(
                elements.categoryMessage,
                "اكتب اسم التصنيف.",
                "error"
            );

            return;
        }


        try {

            await apiFetch(
                "/api/owner/categories",
                {
                    method: "POST",

                    body: JSON.stringify({
                        name
                    })
                }
            );


            elements.categoryName.value =
                "";


            showMessage(
                elements.categoryMessage,
                "تم إنشاء التصنيف بنجاح.",
                "success"
            );


            await loadCategories();


        } catch (error) {

            console.error(
                "Create category error:",
                error
            );


            showMessage(
                elements.categoryMessage,
                error.message ||
                "تعذر إنشاء التصنيف.",
                "error"
            );
        }
    }


    /* =========================================================
       Delete Category
       ========================================================= */

    async function deleteCategory(
        categoryId,
        categoryName
    ) {

        const confirmed =
            window.confirm(
                `هل أنت متأكد من حذف التصنيف "${categoryName}"؟`
            );


        if (!confirmed) {
            return;
        }


        try {

            await apiFetch(
                `/api/owner/categories/${encodeURIComponent(categoryId)}`,
                {
                    method: "DELETE"
                }
            );


            showMessage(
                elements.categoryMessage,
                "تم حذف التصنيف.",
                "success"
            );


            await loadCategories();


        } catch (error) {

            console.error(
                "Delete category error:",
                error
            );


            showMessage(
                elements.categoryMessage,
                error.message ||
                "تعذر حذف التصنيف.",
                "error"
            );
        }
    }


    /* =========================================================
       Scripts
       ========================================================= */

    async function loadScripts() {

        const data =
            await apiFetch(
                "/api/scripts"
            );


        state.scripts =
            Array.isArray(data)
                ? data
                : [];


        renderScriptsList();
    }


    function renderScriptsList() {

        if (!elements.scriptsList) {
            return;
        }


        elements.scriptsList.innerHTML =
            "";


        if (
            state.scripts.length === 0
        ) {

            const empty =
                document.createElement("div");

            empty.textContent =
                "لا توجد سكربتات منشورة حالياً.";

            empty.style.opacity =
                ".6";

            elements.scriptsList.appendChild(
                empty
            );

            return;
        }


        for (
            const script
            of state.scripts
        ) {

            const item =
                document.createElement("div");

            item.className =
                "owner-script";


            /* ---------------------------------------------
               Info
               --------------------------------------------- */

            const info =
                document.createElement("div");

            info.className =
                "owner-script-info";


            const title =
                document.createElement("div");

            title.className =
                "owner-script-title";

            title.textContent =
                script.title ||
                "بدون عنوان";


            const meta =
                document.createElement("div");

            meta.className =
                "owner-script-meta";


            const category =
                script.category ||
                "بدون تصنيف";


            const game =
                script.game ||
                "بدون لعبة";


            meta.textContent =
                `${category} • ${game}`;


            info.appendChild(
                title
            );

            info.appendChild(
                meta
            );


            /* ---------------------------------------------
               Actions
               --------------------------------------------- */

            const actions =
                document.createElement("div");

            actions.className =
                "owner-script-actions";


            const editButton =
                document.createElement("button");

            editButton.type =
                "button";

            editButton.className =
                "owner-button owner-secondary";

            editButton.textContent =
                "تعديل";


            editButton.addEventListener(
                "click",
                () => {
                    startEditScript(script);
                }
            );


            const deleteButton =
                document.createElement("button");

            deleteButton.type =
                "button";

            deleteButton.className =
                "owner-button owner-danger";

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


            item.appendChild(
                info
            );

            item.appendChild(
                actions
            );


            elements.scriptsList.appendChild(
                item
            );
        }
    }


    /* =========================================================
       Create Script
       ========================================================= */

    async function submitScript(event) {

        event.preventDefault();

        clearMessage(
            elements.scriptMessage
        );


        const title =
            elements.scriptTitle
                ?.value
                ?.trim() || "";


        if (!title) {

            showMessage(
                elements.scriptMessage,
                "اكتب اسم السكربت.",
                "error"
            );

            return;
        }


        /*
         * التصنيف:
         *
         * إذا كان المستخدم اختار "بدون تصنيف"
         * تكون القيمة "".
         *
         * وهذا مقبول تماماً.
         */

        const category =
            elements.category
                ?.value
                ?.trim() || "";


        const payload = {

            title,

            description:
                elements.scriptDescription
                    ?.value
                    ?.trim() || "",

            game:
                elements.scriptGame
                    ?.value
                    ?.trim() || "",

            category,

            image:
                elements.scriptImage
                    ?.value
                    ?.trim() || "",

            code:
                elements.scriptCode
                    ?.value || "",

            featured:
                Boolean(
                    elements.scriptFeatured
                        ?.checked
                )
        };


        const editingId =
            state.editingScriptId;


        const isEditing =
            Boolean(editingId);


        const url =
            isEditing
                ? `/api/owner/scripts/${encodeURIComponent(editingId)}`
                : "/api/owner/scripts";


        const method =
            isEditing
                ? "PUT"
                : "POST";


        const originalText =
            elements.publishButton
                ?.textContent ||
            "نشر السكربت";


        if (elements.publishButton) {

            elements.publishButton.disabled =
                true;

            elements.publishButton.textContent =
                isEditing
                    ? "جاري الحفظ..."
                    : "جاري النشر...";
        }


        try {

            const result =
                await apiFetch(
                    url,
                    {
                        method,

                        body: JSON.stringify(
                            payload
                        )
                    }
                );


            showMessage(
                elements.scriptMessage,

                isEditing
                    ? "تم تعديل السكربت بنجاح."
                    : "تم نشر السكربت بنجاح.",

                "success"
            );


            resetScriptForm();


            await loadScripts();


        } catch (error) {

            console.error(
                "Save script error:",
                error
            );


            /*
             * لو انتهت الجلسة
             */

            if (
                error.status === 401
            ) {

                showLogin();

                showMessage(
                    elements.loginMessage,
                    "انتهت جلسة الدخول. سجّل الدخول مرة أخرى.",
                    "error"
                );

                return;
            }


            showMessage(
                elements.scriptMessage,
                error.message ||
                "تعذر حفظ السكربت.",
                "error"
            );


        } finally {

            if (elements.publishButton) {

                elements.publishButton.disabled =
                    false;

                elements.publishButton.textContent =
                    originalText;
            }
        }
    }


    /* =========================================================
       Edit Script
       ========================================================= */

    function startEditScript(script) {

        state.editingScriptId =
            script.id;


        elements.editingScriptId.value =
            script.id;


        elements.scriptTitle.value =
            script.title || "";


        elements.scriptDescription.value =
            script.description || "";


        elements.scriptGame.value =
            script.game || "";


        elements.scriptImage.value =
            script.image || "";


        elements.scriptCode.value =
            script.code || "";


        elements.scriptFeatured.checked =
            Boolean(script.featured);


        /*
         * التصنيف اختياري.
         */

        renderCategorySelect();


        const category =
            script.category || "";


        const matchingOption =
            Array.from(
                elements.category.options
            ).find(
                option =>
                    option.value.toLowerCase() ===
                    category.toLowerCase()
            );


        if (matchingOption) {

            elements.category.value =
                matchingOption.value;

        } else {

            elements.category.value =
                "";
        }


        if (elements.editBadge) {

            elements.editBadge.style.display =
                "block";
        }


        if (elements.publishButton) {

            elements.publishButton.textContent =
                "حفظ التعديلات";
        }


        if (elements.cancelEditButton) {

            elements.cancelEditButton.style.display =
                "inline-block";
        }


        clearMessage(
            elements.scriptMessage
        );


        elements.scriptForm.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }


    /* =========================================================
       Reset Script Form
       ========================================================= */

    function resetScriptForm() {

        state.editingScriptId =
            null;


        if (elements.editingScriptId) {
            elements.editingScriptId.value =
                "";
        }


        if (elements.scriptForm) {
            elements.scriptForm.reset();
        }


        /*
         * بعد reset نضمن أن التصنيف يرجع
         * إلى "بدون تصنيف".
         */

        renderCategorySelect();


        if (elements.category) {
            elements.category.value =
                "";
        }


        if (elements.editBadge) {

            elements.editBadge.style.display =
                "none";
        }


        if (elements.publishButton) {

            elements.publishButton.textContent =
                "نشر السكربت";
        }


        if (elements.cancelEditButton) {

            elements.cancelEditButton.style.display =
                "none";
        }
    }


    /* =========================================================
       Delete Script
       ========================================================= */

    async function deleteScript(
        scriptId,
        scriptTitle
    ) {

        const confirmed =
            window.confirm(
                `هل أنت متأكد من حذف السكربت "${scriptTitle}"؟`
            );


        if (!confirmed) {
            return;
        }


        try {

            await apiFetch(
                `/api/owner/scripts/${encodeURIComponent(scriptId)}`,
                {
                    method: "DELETE"
                }
            );


            /*
             * إذا كان السكربت المحذوف هو
             * الذي نعدله حالياً، نلغي التعديل.
             */

            if (
                state.editingScriptId ===
                scriptId
            ) {
                resetScriptForm();
            }


            showMessage(
                elements.scriptMessage,
                "تم حذف السكربت.",
                "success"
            );


            await loadScripts();


        } catch (error) {

            console.error(
                "Delete script error:",
                error
            );


            showMessage(
                elements.scriptMessage,
                error.message ||
                "تعذر حذف السكربت.",
                "error"
            );
        }
    }


    /* =========================================================
       Events
       ========================================================= */

    function setupEvents() {

        if (elements.loginForm) {

            elements.loginForm.addEventListener(
                "submit",
                login
            );
        }


        if (elements.logoutButton) {

            elements.logoutButton.addEventListener(
                "click",
                logout
            );
        }


        if (elements.categoryForm) {

            elements.categoryForm.addEventListener(
                "submit",
                createCategory
            );
        }


        if (elements.scriptForm) {

            elements.scriptForm.addEventListener(
                "submit",
                submitScript
            );
        }


        if (elements.cancelEditButton) {

            elements.cancelEditButton.addEventListener(
                "click",
                () => {
                    resetScriptForm();

                    clearMessage(
                        elements.scriptMessage
                    );
                }
            );
        }
    }


    /* =========================================================
       Start
       ========================================================= */

    async function init() {

        setupEvents();

        await checkSession();
    }


    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            init
        );

    } else {

        init();
    }

})();