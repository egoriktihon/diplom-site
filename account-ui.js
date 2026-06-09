(function () {
    const TOKEN_KEY = "clinicAuthToken";
    const REDIRECT_KEY = "clinicPostAuthRedirect";
    const SLOTS = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"];
    const statusLabels = { scheduled: "\u0417\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0430", completed: "\u041f\u0440\u043e\u0448\u043b\u0430", no_show: "\u041f\u0430\u0446\u0438\u0435\u043d\u0442 \u043d\u0435 \u043f\u0440\u0438\u0448\u0435\u043b", failed: "\u0417\u0430\u043f\u0438\u0441\u044c \u043d\u0435 \u0443\u0434\u0430\u043b\u0430\u0441\u044c" };
    const categoryLabels = { consultation: "\u041a\u043e\u043d\u0441\u0443\u043b\u044c\u0442\u0430\u0446\u0438\u0438", diagnostics: "\u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430", analysis: "\u0410\u043d\u0430\u043b\u0438\u0437\u044b", cardio: "\u041a\u0430\u0440\u0434\u0438\u043e\u043b\u043e\u0433\u0438\u044f", checkup: "Check-up", treatment: "\u041b\u0435\u0447\u0435\u043d\u0438\u0435", general: "\u041e\u0431\u0449\u0435\u0435" };

    let currentUser = null;
    let doctorsCatalog = [];
    let servicesCatalog = [];

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const token = () => localStorage.getItem(TOKEN_KEY);
    const setToken = (value) => localStorage.setItem(TOKEN_KEY, value);
    const clearToken = () => localStorage.removeItem(TOKEN_KEY);
    const fmtDate = (value) => new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
    const fmtPrice = (value) => `${Number(value || 0).toLocaleString("ru-RU")} \u20bd`;
    const initials = (name = "\u041f\u0430\u0446\u0438\u0435\u043d\u0442") => name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "\u041f";
    const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));

    async function api(action, options = {}) {
        const headers = new Headers(options.headers || {});
        if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
        if (token()) headers.set("Authorization", `Bearer ${token()}`);
        const response = await fetch(`/api?action=${encodeURIComponent(action)}`, { method: options.method || "GET", headers, body: options.body, credentials: "same-origin" });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(payload.error || "\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0440\u043e\u0441\u0430");
            error.status = response.status;
            error.code = payload.code;
            throw error;
        }
        return payload;
    }

    function toast(message, type) {
        let node = $(".account-toast");
        if (!node) {
            node = document.createElement("div");
            node.className = "account-toast";
            document.body.appendChild(node);
        }
        node.className = `account-toast ${type || ""}`;
        node.textContent = message;
        node.classList.add("show");
        setTimeout(() => node.classList.remove("show"), 2600);
    }

    function formMessage(form, text, type) {
        const node = $(".auth-message", form);
        if (!node) return;
        node.textContent = text;
        node.className = `auth-message ${type || ""}`;
    }

    async function hydrateUser() {
        if (!token()) {
            currentUser = null;
            return;
        }
        try {
            currentUser = (await api("me")).user;
        } catch {
            clearToken();
            currentUser = null;
        }
    }

    function renderHeaderAccount() {
        $$(".account-widget").forEach((node) => node.remove());
        const nav = $(".header .nav");
        if (!nav) return;
        const mainButton = nav.querySelector(":scope > a.btn.primary");
        if (!currentUser) {
            mainButton?.classList.remove("account-hidden");
            return;
        }
        mainButton?.classList.add("account-hidden");
        const href = currentUser.role === "admin" ? "admin.html" : "profile.html";
        const label = currentUser.role === "admin" ? "\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430" : currentUser.role === "doctor" ? "\u041a\u0430\u0431\u0438\u043d\u0435\u0442 \u0432\u0440\u0430\u0447\u0430" : "\u041b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442";
        const widget = document.createElement("div");
        widget.className = "account-widget";
        widget.innerHTML = `
            <button class="account-trigger" type="button">${initials(currentUser.full_name)}</button>
            <div class="account-panel" aria-hidden="true">
                <div class="account-user">
                    <div class="account-avatar">${initials(currentUser.full_name)}</div>
                    <div><h3>${currentUser.full_name}</h3><p>${currentUser.phone || ""}</p><p class="account-caption">${currentUser.email || ""}</p></div>
                </div>
                <div class="account-actions">
                    <a class="account-action" href="${href}">${label}</a>
                    <button class="account-logout" type="button">\u0412\u044b\u0439\u0442\u0438</button>
                </div>
            </div>`;
        nav.appendChild(widget);
        const panel = $(".account-panel", widget);
        $(".account-trigger", widget).addEventListener("click", (event) => {
            event.stopPropagation();
            panel.classList.toggle("open");
        });
        $(".account-logout", widget).addEventListener("click", async () => {
            await api("logout", { method: "POST" }).catch(() => {});
            clearToken();
            currentUser = null;
            renderHeaderAccount();
            if (location.pathname.endsWith("profile.html") || location.pathname.endsWith("admin.html")) location.href = "auth.html#login";
        });
        document.addEventListener("click", (event) => {
            if (!widget.contains(event.target)) panel.classList.remove("open");
        }, { once: true });
    }

    function bindAuthForms() {
        const registerForm = $("#register-panel .auth-form");
        const loginForm = $("#login-panel .auth-form");
        if (registerForm && registerForm.dataset.bound !== "true") {
            registerForm.dataset.bound = "true";
            registerForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                const inputs = $$("input", registerForm);
                try {
                    const payload = await api("register", { method: "POST", body: JSON.stringify({ full_name: inputs[0].value.trim(), phone: inputs[1].value.trim(), email: inputs[2].value.trim(), password: inputs[3].value.trim() }) });
                    setToken(payload.token);
                    currentUser = payload.user;
                    location.href = sessionStorage.getItem(REDIRECT_KEY) || "profile.html";
                } catch (error) {
                    formMessage(registerForm, error.message, "error");
                }
            });
        }
        if (loginForm && loginForm.dataset.bound !== "true") {
            loginForm.dataset.bound = "true";
            loginForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                const inputs = $$("input", loginForm);
                try {
                    const payload = await api("login", { method: "POST", body: JSON.stringify({ login: inputs[0].value.trim(), password: inputs[1].value.trim() }) });
                    setToken(payload.token);
                    currentUser = payload.user;
                    location.href = sessionStorage.getItem(REDIRECT_KEY) || (currentUser.role === "admin" ? "admin.html" : "profile.html");
                } catch (error) {
                    formMessage(loginForm, error.message, "error");
                }
            });
        }
    }

    function bindServiceFilters() {
        $$(".service-tabs [data-service-filter]").forEach((button) => {
            button.addEventListener("click", () => {
                $$(".service-tabs .btn").forEach((item) => item.classList.remove("active"));
                button.classList.add("active");
                const filter = button.dataset.serviceFilter;
                $$(".service-card").forEach((card) => {
                    card.style.display = filter === "all" || card.dataset.category === filter ? "" : "none";
                });
            });
        });
    }

    async function renderServices() {
        const grid = $(".services-grid");
        const homeGrid = $(".services.container .grid");
        const priceTable = $(".price-table-card");
        if (!grid && !homeGrid && !priceTable) return;
        try {
            servicesCatalog = (await api("services")).services || [];
            if (grid) {
                grid.innerHTML = servicesCatalog.map((service) => `
                    <article class="service-card" data-category="${service.category_key}">
                        <img src="${service.image_path}" alt="${service.name}">
                        <h3>${service.name}</h3>
                        <p>${service.short_description || service.full_description || ""}</p>
                        <div class="service-price">${fmtPrice(service.price)}</div>
                        <button class="btn primary" type="button" data-service-id="${service.id}">\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f</button>
                    </article>`).join("");
            }
            if (homeGrid) {
                homeGrid.innerHTML = servicesCatalog.slice(0, 3).map((service) => `
                    <div class="card"><img src="${service.image_path}" alt="${service.name}"><h3>${service.name}</h3><p>${service.short_description || ""}</p><a class="btn primary" href="services.html">\u0423\u0441\u043b\u0443\u0433\u0438</a></div>`).join("");
            }
            if (priceTable) {
                priceTable.innerHTML = `
                    <div class="price-row price-head">
                        <span>\u0423\u0441\u043b\u0443\u0433\u0430</span>
                        <span>\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435</span>
                        <span>\u0426\u0435\u043d\u0430</span>
                        <span>\u0417\u0430\u043f\u0438\u0441\u044c</span>
                    </div>
                    ${servicesCatalog.map((service) => `
                        <div class="price-row">
                            <div class="service-cell">
                                <img src="${service.image_path}" alt="${service.name}">
                                <span>${service.name}</span>
                            </div>
                            <p>${service.short_description || service.full_description || ""}</p>
                            <strong>${fmtPrice(service.price)}</strong>
                            <button class="btn primary" type="button" data-service-id="${service.id}">\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f</button>
                        </div>`).join("")}`;
            }
        } catch {}
    }

    function renderDoctorFilters(doctors) {
        const root = $(".doctor-filter .filter-buttons");
        if (!root) return;
        const labels = new Map([["all", "\u0412\u0441\u0435 \u0432\u0440\u0430\u0447\u0438"]]);
        doctors.forEach((doctor) => labels.set(doctor.specialty_key || "other", doctor.specialty_name || "\u0414\u0440\u0443\u0433\u043e\u0435"));
        root.innerHTML = Array.from(labels, ([key, label]) => `<button class="btn primary${key === "all" ? " active" : ""}" type="button" data-specialty="${key}">${label}</button>`).join("");
    }

    function bindDoctorFilters() {
        const search = $(".doctor-search");
        const cards = () => $$(".doctor-card");
        const apply = () => {
            const active = $(".doctor-filter .btn.active")?.dataset.specialty || "all";
            const query = (search?.value || "").trim().toLowerCase();
            cards().forEach((card) => {
                const okSpecialty = active === "all" || card.dataset.specialty === active;
                const okSearch = !query || card.textContent.toLowerCase().includes(query);
                card.style.display = okSpecialty && okSearch ? "" : "none";
            });
        };
        $$(".doctor-filter .btn").forEach((button) => button.addEventListener("click", () => {
            $$(".doctor-filter .btn").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            apply();
        }));
        search?.addEventListener("input", apply);
    }

    async function renderDoctors() {
        const grid = $(".doctors-list .grid");
        const homeGrid = $(".doctors.container .grid");
        if (!grid && !homeGrid) return;
        try {
            doctorsCatalog = (await api("doctors")).doctors || [];
            const card = (doctor) => `
                <div class="doctor-card" data-specialty="${doctor.specialty_key || "other"}">
                    <img src="${doctor.image_path}" alt="${doctor.full_name}">
                    <div class="doctor-info">
                        <h3>${doctor.full_name}</h3>
                        <p>${doctor.specialty_name || ""}</p>
                        <div class="doctor-actions">
                            <button class="btn primary" type="button" data-doctor-id="${doctor.id}">\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f</button>
                            <button class="btn show-more" type="button">\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435</button>
                        </div>
                        <button class="btn close-btn" type="button">x</button>
                        <div class="doctor-more"><p>${doctor.experience_text || ""}. ${doctor.description || ""}</p></div>
                    </div>
                </div>`;
            if (grid) {
                renderDoctorFilters(doctorsCatalog);
                grid.innerHTML = doctorsCatalog.map(card).join("");
                bindDoctorFilters();
            }
            if (homeGrid) {
                homeGrid.innerHTML = doctorsCatalog.slice(0, 3).map((doctor) => `<div class="doctor-card"><img src="${doctor.image_path}" alt="${doctor.full_name}"><h3>${doctor.full_name}</h3><p>${doctor.specialty_name || ""}</p><a href="doctors.html" class="btn primary">\u0412\u0440\u0430\u0447\u0438</a></div>`).join("");
            }
            $$(".show-more").forEach((button) => button.addEventListener("click", () => button.closest(".doctor-card").classList.add("active")));
            $$(".close-btn").forEach((button) => button.addEventListener("click", (event) => {
                event.stopPropagation();
                button.closest(".doctor-card").classList.remove("active");
            }));
        } catch {}
    }

    function doctorsForService(service) {
        if (!service) return doctorsCatalog;
        if (service.doctor_ids?.length) {
            const linkedDoctors = doctorsCatalog.filter((doctor) => service.doctor_ids.includes(doctor.id));
            if (linkedDoctors.length) return linkedDoctors;
        }
        if (service.specialty_id) {
            const specialtyDoctors = doctorsCatalog.filter((doctor) => doctor.specialty_id === service.specialty_id);
            if (specialtyDoctors.length) return specialtyDoctors;
        }
        if (service.specialty_key) {
            const specialtyDoctors = doctorsCatalog.filter((doctor) => doctor.specialty_key === service.specialty_key);
            if (specialtyDoctors.length) return specialtyDoctors;
        }
        return doctorsCatalog;
    }

    function servicesForDoctor(doctor) {
        if (!doctor) return servicesCatalog;
        if (doctor.service_ids?.length) {
            return servicesCatalog.filter((service) => doctor.service_ids.includes(service.id));
        }
        const bySpecialty = servicesCatalog.filter((service) => (service.specialty_id && service.specialty_id === doctor.specialty_id) || (service.specialty_key && service.specialty_key === doctor.specialty_key));
        return bySpecialty.length ? bySpecialty : servicesCatalog;
    }

    function openAppointment(service, fixedDoctor) {
        const modal = document.createElement("div");
        modal.className = "appointment-modal open";
        const services = fixedDoctor ? servicesForDoctor(fixedDoctor) : [service].filter(Boolean);
        const doctors = fixedDoctor ? [fixedDoctor] : doctorsForService(service);
        const serviceSelect = service
            ? `<input type="hidden" name="service_id" value="${service.id}">`
            : `<label><span>\u0423\u0441\u043b\u0443\u0433\u0430</span><select name="service_id" required>${services.map((item) => `<option value="${item.id}">${item.name} - ${fmtPrice(item.price)}</option>`).join("")}</select></label>`;
        const doctorSelect = fixedDoctor
            ? `<input type="hidden" name="doctor_id" value="${fixedDoctor.id}"><div class="appointment-fixed">\u0412\u0440\u0430\u0447: ${fixedDoctor.full_name} - ${fixedDoctor.specialty_name || ""}</div>`
            : `<label><span>\u0412\u0440\u0430\u0447</span><select name="doctor_id" required>${doctors.map((doctor) => `<option value="${doctor.id}">${doctor.full_name} - ${doctor.specialty_name}</option>`).join("")}</select></label>`;
        modal.innerHTML = `
            <div class="appointment-modal__backdrop"></div>
            <div class="appointment-modal__dialog">
                <button class="appointment-modal__close" type="button">x</button>
                <div class="appointment-modal__body">
                    <h2>\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f \u043d\u0430 \u043f\u0440\u0438\u0435\u043c</h2>
                    <p>${service ? service.name : "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0443\u0441\u043b\u0443\u0433\u0443 \u0438 \u0443\u0434\u043e\u0431\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f"}</p>
                    <form class="appointment-form">
                        ${serviceSelect}
                        ${doctorSelect}
                        <label><span>\u0414\u0430\u0442\u0430</span><input type="date" name="date" required></label>
                        <label><span>\u0412\u0440\u0435\u043c\u044f</span><select name="time">${SLOTS.map((slot) => `<option value="${slot}">${slot}</option>`).join("")}</select></label>
                        <label><span>\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439</span><textarea name="notes" rows="3"></textarea></label>
                        <p class="auth-message" aria-live="polite"></p>
                        <button class="btn primary" type="submit">\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f</button>
                    </form>
                </div>
            </div>`;
        document.body.appendChild(modal);
        $(".appointment-modal__backdrop", modal).addEventListener("click", () => modal.remove());
        $(".appointment-modal__close", modal).addEventListener("click", () => modal.remove());
        const form = $(".appointment-form", modal);
        const dateInput = $("input[name='date']", form);
        const doctorInput = $("[name='doctor_id']", form);
        const timeSelect = $("select[name='time']", form);
        const submitButton = $("button[type='submit']", form);
        const renderSlots = (busyTimes = []) => {
            const busy = new Set(busyTimes.map((time) => String(time).slice(0, 5)));
            const selected = timeSelect.value;
            const freeSlots = SLOTS.filter((slot) => !busy.has(slot));
            timeSelect.innerHTML = freeSlots.map((slot) => `<option value="${slot}" ${slot === selected ? "selected" : ""}>${slot}</option>`).join("");
            const hasSlots = freeSlots.length > 0;
            timeSelect.disabled = !hasSlots;
            submitButton.disabled = !hasSlots;
            formMessage(form, hasSlots ? "" : "\u041d\u0430 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0434\u0430\u0442\u0443 \u043d\u0435\u0442 \u0441\u0432\u043e\u0431\u043e\u0434\u043d\u043e\u0433\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438.", hasSlots ? "" : "error");
        };
        const refreshSlots = async () => {
            const doctorId = Number(doctorInput?.value || 0);
            const appointmentDate = dateInput?.value || "";
            if (!doctorId || !appointmentDate) {
                renderSlots([]);
                return;
            }
            try {
                const payload = await api("appointments.busy", { method: "POST", body: JSON.stringify({ doctor_id: doctorId, appointment_date: appointmentDate }) });
                renderSlots(payload.busy_times || []);
            } catch {
                renderSlots([]);
            }
        };
        dateInput?.addEventListener("change", refreshSlots);
        doctorInput?.addEventListener("change", refreshSlots);
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!currentUser) {
                sessionStorage.setItem(REDIRECT_KEY, location.pathname.split("/").pop() || "profile.html");
                location.href = "auth.html#login";
                return;
            }
            const data = new FormData(event.currentTarget);
            if (!data.get("time")) {
                formMessage(event.currentTarget, "\u041d\u0430 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0434\u0430\u0442\u0443 \u043d\u0435\u0442 \u0441\u0432\u043e\u0431\u043e\u0434\u043d\u043e\u0433\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438.", "error");
                return;
            }
            const doctorId = Number(data.get("doctor_id") || 0);
            const serviceId = Number(data.get("service_id") || service?.id || 0);
            const selectedService = servicesCatalog.find((item) => item.id === serviceId) || service;
            const doctor = doctorsCatalog.find((item) => item.id === doctorId);
            try {
                await api("appointments.create", { method: "POST", body: JSON.stringify({ title: selectedService.name, subtitle: doctor ? doctor.full_name : selectedService.name, price: fmtPrice(selectedService.price), doctor_id: doctorId, service_id: selectedService.id, appointment_date: data.get("date"), appointment_time: data.get("time"), notes: data.get("notes") }) });
                toast("\u0417\u0430\u043f\u0438\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u043d\u0430");
                modal.remove();
                await hydrateUser();
            } catch (error) {
                const isBusyTime = error.code === "appointment_time_busy" || error.status === 409;
                const message = isBusyTime
                    ? "\u041d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e \u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f \u043d\u0430 \u044d\u0442\u043e \u0432\u0440\u0435\u043c\u044f, \u043f\u043e\u0442\u043e\u043c\u0443 \u0447\u0442\u043e \u043e\u043d\u043e \u0443\u0436\u0435 \u0437\u0430\u043d\u044f\u0442\u043e."
                    : error.message;
                formMessage(event.currentTarget, message, "error");
                $(".auth-message", event.currentTarget)?.scrollIntoView({ behavior: "smooth", block: "center" });
                toast(message, "error");
                if (isBusyTime) refreshSlots();
            }
        });
    }

    function bindAppointmentButtons() {
        document.addEventListener("click", async (event) => {
            const serviceButton = event.target.closest("[data-service-id]");
            const doctorButton = event.target.closest("[data-doctor-id]");
            const priceLink = event.target.closest(".price-row a.btn.primary[href*='auth.html']");
            if (!serviceButton && !doctorButton && !priceLink) return;
            event.preventDefault();
            if (!servicesCatalog.length) servicesCatalog = (await api("services")).services || [];
            if (!doctorsCatalog.length) doctorsCatalog = (await api("doctors")).doctors || [];
            if (serviceButton) {
                const service = servicesCatalog.find((item) => item.id === Number(serviceButton.dataset.serviceId));
                if (service) openAppointment(service);
                return;
            }
            if (priceLink) {
                const serviceName = $(".service-cell span", priceLink.closest(".price-row"))?.textContent.trim();
                const service = servicesCatalog.find((item) => item.name === serviceName);
                if (service) openAppointment(service);
                return;
            }
            const doctor = doctorsCatalog.find((item) => item.id === Number(doctorButton.dataset.doctorId));
            if (doctor) openAppointment(null, doctor);
        });
    }

    async function renderProfile() {
        const root = $("[data-profile-page]");
        if (!root) return;
        if (!currentUser) {
            sessionStorage.setItem(REDIRECT_KEY, "profile.html");
            location.href = "auth.html#login";
            return;
        }
        $("[data-profile-avatar]", root).textContent = initials(currentUser.full_name);
        $("[data-profile-name]", root).textContent = currentUser.full_name;
        $("[data-profile-email]", root).textContent = currentUser.email || "";
        $("[data-profile-phone]", root).textContent = currentUser.phone || "";
        $("[data-profile-created]", root).textContent = fmtDate(currentUser.created_at);
        const list = $("[data-profile-appointments]", root);
        if (currentUser.role === "doctor") {
            const appointments = (await api("doctor.dashboard")).appointments || [];
            $("[data-profile-count]", root).textContent = String(appointments.length);
            list.innerHTML = appointments.length ? appointments.map((item) => `
                <article class="profile-appointment-card">
                    <div><p class="profile-appointment-date">${fmtDate(item.appointment_date)} ${String(item.appointment_time).slice(0, 5)}</p><h3>${item.title}</h3><p>${item.patient_name} ${item.patient_phone}</p><p>${item.subtitle}</p><p class="appointment-status">${statusLabels[item.status] || statusLabels.scheduled}</p></div>
                    <div class="appointment-actions"><button class="btn primary" data-status-id="${item.id}" data-status="completed">\u041f\u0440\u043e\u0448\u043b\u0430</button><button class="btn secondary" data-status-id="${item.id}" data-status="no_show">\u041d\u0435 \u043f\u0440\u0438\u0448\u0435\u043b</button><button class="account-logout profile-cancel-btn" data-status-id="${item.id}" data-status="failed">\u041d\u0435 \u0443\u0434\u0430\u043b\u0430\u0441\u044c</button></div>
                </article>`).join("") : `<div class="profile-empty"><h3>\u0417\u0430\u043f\u0438\u0441\u0435\u0439 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442</h3></div>`;
            $$("[data-status-id]", list).forEach((button) => button.addEventListener("click", async () => {
                await api("doctor.appointments.status", { method: "POST", body: JSON.stringify({ id: Number(button.dataset.statusId), status: button.dataset.status }) });
                renderProfile();
            }));
            return;
        }
        const appointments = currentUser.appointments || [];
        $("[data-profile-count]", root).textContent = String(appointments.length);
        list.innerHTML = appointments.length ? appointments.map((item) => `
            <article class="profile-appointment-card"><div><p class="profile-appointment-date">${fmtDate(item.appointment_date)} ${String(item.appointment_time).slice(0, 5)}</p><h3>${item.title}</h3><p>${item.subtitle}</p><p class="appointment-status">${statusLabels[item.status] || statusLabels.scheduled}</p></div><button class="account-logout profile-cancel-btn" data-cancel-id="${item.id}">\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c</button></article>`).join("") : `<div class="profile-empty"><h3>\u0417\u0430\u043f\u0438\u0441\u0435\u0439 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442</h3><a href="services.html" class="btn primary">\u041a \u0443\u0441\u043b\u0443\u0433\u0430\u043c</a></div>`;
        $$("[data-cancel-id]", list).forEach((button) => button.addEventListener("click", async () => {
            await api("appointments.cancel", { method: "POST", body: JSON.stringify({ id: Number(button.dataset.cancelId) }) });
            await hydrateUser();
            renderProfile();
        }));
    }

    async function renderAdmin() {
        const root = $("[data-admin-page]");
        if (!root) return;
        if (!currentUser) {
            sessionStorage.setItem(REDIRECT_KEY, "admin.html");
            location.href = "auth.html#login";
            return;
        }
        if (currentUser.role !== "admin") {
            location.href = "profile.html";
            return;
        }
        const payload = await api("admin.dashboard");
        $("[data-admin-summary]", root).innerHTML = Object.entries({ "\u041f\u0430\u0446\u0438\u0435\u043d\u0442\u044b": payload.counts.users, "\u0412\u0440\u0430\u0447\u0438": payload.counts.doctors, "\u0421\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u0438": payload.counts.specialties, "\u0423\u0441\u043b\u0443\u0433\u0438": payload.counts.services, "\u0417\u0430\u043f\u0438\u0441\u0438": payload.counts.appointments }).map(([label, value]) => `<div class="admin-summary-card"><span>${label}</span><strong>${value}</strong></div>`).join("");
        $("[data-admin-specialties]", root).innerHTML = payload.specialties.map((item) => `<article class="admin-card"><div><h3>${item.name}</h3><p>${item.specialty_key}</p></div><button class="account-logout delete-icon" data-delete-specialty="${item.id}">x</button></article>`).join("");
        $("[data-admin-doctors]", root).innerHTML = payload.doctors.map((item) => `<article class="admin-card"><div><h3>${item.full_name}</h3><p>${item.specialty_name}</p><p>${item.experience_text || ""}</p><p>${item.account_email || ""}</p></div><button class="account-logout delete-icon" data-delete-doctor="${item.id}">x</button></article>`).join("");
        $("[data-admin-services]", root).innerHTML = payload.services.map((item) => `<article class="admin-card"><div><h3>${item.name}</h3><p>${fmtPrice(item.price)} ${categoryLabels[item.category_key] || ""}</p></div><button class="account-logout delete-icon" data-delete-service="${item.id}">x</button></article>`).join("");
        $("[data-admin-appointments]", root).innerHTML = payload.appointments.length ? payload.appointments.map((item) => `<article class="admin-appointment-card"><div><h3>${item.title}</h3><p>${fmtDate(item.appointment_date)} ${String(item.appointment_time).slice(0, 5)}</p><p>${item.patient_name} ${item.patient_phone}</p><p>${item.doctor_name || ""}</p><p class="appointment-status">${statusLabels[item.status] || statusLabels.scheduled}</p></div><button class="account-logout profile-cancel-btn" data-delete-appointment="${item.id}">\u0423\u0434\u0430\u043b\u0438\u0442\u044c</button></article>`).join("") : `<div class="profile-empty"><h3>\u0417\u0430\u043f\u0438\u0441\u0435\u0439 \u043d\u0435\u0442</h3></div>`;
        $$('select[name="specialty_id"]', root).forEach((select) => {
            const first = select.closest("[data-admin-service-form]") ? `<option value="">\u0411\u0435\u0437 \u0441\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u0438</option>` : `<option value="">\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u044c</option>`;
            select.innerHTML = first + payload.specialties.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
        });
        const serviceSelect = $("[data-admin-service-select]", root);
        if (serviceSelect) serviceSelect.innerHTML = `<option value="">\u0423\u0441\u043b\u0443\u0433\u0430</option>` + payload.services.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
    }

    function bindAdminForms() {
        const root = $("[data-admin-page]");
        if (!root || root.dataset.bound === "true") return;
        root.dataset.bound = "true";
        const selected = new Set();
        $("[data-admin-add-service]", root)?.addEventListener("click", () => {
            const id = Number($("[data-admin-service-select]", root).value || 0);
            if (id) selected.add(id);
            $("[data-admin-selected-services]", root).innerHTML = Array.from(selected).map((id) => `<span class="admin-selected-item">${id}</span>`).join("");
        });
        $("[data-admin-specialty-form]", root)?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            await api("admin.specialties.create", { method: "POST", body: JSON.stringify({ name: data.get("name"), specialty_key: data.get("specialty_key") }) });
            event.currentTarget.reset();
            renderAdmin();
        });
        $("[data-admin-doctor-form]", root)?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const data = new FormData(form);
            const specialty = (await api("admin.dashboard")).specialties.find((item) => item.id === Number(data.get("specialty_id")));
            const file = data.get("image_file");
            const image_data = file && file.size ? await new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || "")); reader.readAsDataURL(file); }) : "";
            await api("admin.doctors.create", { method: "POST", body: JSON.stringify({ full_name: data.get("full_name"), specialty_id: Number(data.get("specialty_id")), specialty_name: specialty?.name || "", specialty_key: specialty?.specialty_key || "other", account_login: data.get("account_login"), account_phone: data.get("account_phone"), account_password: data.get("account_password"), experience_text: data.get("experience_text"), description: data.get("description"), image_name: file?.name || "", image_data, service_ids: Array.from(selected) }) });
            form.reset();
            selected.clear();
            renderAdmin();
        });
        $("[data-admin-service-form]", root)?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const file = data.get("image_file");
            const image_data = file && file.size ? await new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || "")); reader.readAsDataURL(file); }) : "";
            await api("admin.services.create", { method: "POST", body: JSON.stringify({ name: data.get("name"), price: Number(data.get("price")), category_key: data.get("category_key"), specialty_id: Number(data.get("specialty_id") || 0), image_name: file?.name || "", image_data }) });
            event.currentTarget.reset();
            renderAdmin();
        });
        root.addEventListener("click", async (event) => {
            const actions = [["deleteDoctor", "admin.doctors.delete"], ["deleteService", "admin.services.delete"], ["deleteSpecialty", "admin.specialties.delete"], ["deleteAppointment", "admin.appointments.delete"]];
            for (const [key, action] of actions) {
                const id = event.target.dataset[key];
                if (id) {
                    await api(action, { method: "POST", body: JSON.stringify({ id: Number(id) }) });
                    renderAdmin();
                }
            }
            const toggle = event.target.dataset.toggleList;
            if (toggle) {
                const list = root.querySelector(`[data-admin-${toggle}]`);
                if (list) list.classList.toggle("collapsed");
            }
        });
    }

    document.addEventListener("DOMContentLoaded", async () => {
        await hydrateUser();
        renderHeaderAccount();
        bindAuthForms();
        bindServiceFilters();
        await renderServices();
        await renderDoctors();
        bindAppointmentButtons();
        await renderProfile();
        bindAdminForms();
        await renderAdmin();
    });
})();
