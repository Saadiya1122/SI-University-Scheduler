console.log("UniPlan timetable loaded");

let selectedQuarter = "Q1";
let selectedWeekIndex = 0;
let selectedModule = "all";
let selectedDay = null;
let currentView = "week";

const scheduleConfig = window.UNIPLAN_SCHEDULE_CONFIG || {
    teaching_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    teaching_start: "09:00",
    teaching_end: "17:00",
    scheduling_interval_minutes: 30
};

const days = scheduleConfig.teaching_days || ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
selectedDay = days[0] || "Monday";

const teachingStart = parseInt(scheduleConfig.teaching_start.split(":")[0], 10);
const teachingEnd = parseInt(scheduleConfig.teaching_end.split(":")[0], 10);
const schedulingIntervalMinutes = Number(scheduleConfig.scheduling_interval_minutes) || 30;
const hourHeight = 72;
const previewLimit = 2;
const dayLaneWidth = 190;
const dayLaneGap = 8;

const quarterFilter = document.getElementById("quarterFilter");
const weekFilter = document.getElementById("weekFilter");
const campusFilter = document.getElementById("campusFilter");
const moduleSearch = document.getElementById("moduleSearch");
const moduleDropdown = document.getElementById("moduleDropdown");
const moduleResults = document.getElementById("moduleResults");
const weekView = document.getElementById("weekView");
const dayView = document.getElementById("dayView");
const weekCalendarBody = document.getElementById("weekCalendarBody");
const weekTimeColumn = document.getElementById("weekTimeColumn");
const dayDetailContent = document.getElementById("dayDetailContent");
const dayEmptyState = document.getElementById("dayEmptyState");
const sessionModal = document.getElementById("sessionModal");
const sessionModalClose = document.getElementById("sessionModalClose");
const sessionModalDone = document.getElementById("sessionModalDone");
const sessionModalBackdrop = document.getElementById("sessionModalBackdrop");

function cleanText(value) {
    return String(value || "").trim().toLowerCase();
}

function normaliseDay(value) {
    return String(value || "").trim();
}

function timeToMinutes(time) {
    const parts = String(time || "00:00").split(":");
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

function minutesToTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

function getEndTime(session) {
    const start = timeToMinutes(session.start_time);
    const duration = Number(session.duration_hours || 0) * 60;
    return minutesToTime(start + duration);
}

function getCurrentWeek() {
    const weeks = calendarWeeks[selectedQuarter] || [];
    return weeks[selectedWeekIndex] || null;
}

function getDayDate(day) {
    const week = getCurrentWeek();
    if (!week) return null;

    const startDate = new Date(`${week.start}T00:00:00`);
    const index = days.indexOf(day);
    const date = new Date(startDate);

    date.setDate(startDate.getDate() + Math.max(index, 0));
    return date;
}

function getDateFormat() {
    return localStorage.getItem("uniplan-date-format") || "long";
}

function formatDateParts(date) {
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = String(date.getFullYear());
    return { day, month, year };
}

function formatDateFull(date) {
    const parts = formatDateParts(date);

    if (getDateFormat() === "short") {
        return `${parts.day}/${parts.month}/${parts.year.slice(-2)}`;
    }

    return date.getDate() + " " + [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"
    ][date.getMonth()] + " " + parts.year;
}

function formatDateShort(date) {
    const parts = formatDateParts(date);

    if (getDateFormat() === "short") {
        return `${parts.day}/${parts.month}`;
    }

    return date.getDate() + " " + [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"
    ][date.getMonth()];
}
function updateWeekDisplay() {
    const week = getCurrentWeek();
    if (!week) return;

    const weekTitle = document.getElementById("weekTitle");
    const weekRange = document.getElementById("weekRange");
    const monthYear = document.getElementById("monthYear");

    if (weekTitle) weekTitle.textContent = `Week ${week.week}`;

    if (weekRange) {
        if (week.start_display && week.end_display) {
            weekRange.textContent = `${week.start_display} – ${week.end_display}`;
        } else {
            const start = new Date(`${week.start}T00:00:00`);
            const end = new Date(start);
            end.setDate(start.getDate() + days.length - 1);
            weekRange.textContent = `${formatDateFull(start)} – ${formatDateFull(end)}`;
        }
    }

    if (monthYear) {
        const start = new Date(`${week.start}T00:00:00`);
        monthYear.textContent = start.toLocaleDateString("en-GB", {
            month: "long",
            year: "numeric"
        });
    }

    document.querySelectorAll(".week-day-header").forEach(header => {
        const day = header.dataset.day;
        const date = getDayDate(day);
        const dateElement = header.querySelector("[data-day-date]");
        if (date && dateElement) dateElement.textContent = formatDateShort(date);
    });
}

function loadWeeks() {
    if (!weekFilter) return;

    const weeks = calendarWeeks[selectedQuarter] || [];
    weekFilter.innerHTML = "";

    weeks.forEach((week, index) => {
        const option = document.createElement("option");
        option.value = index;

        const start = new Date(`${week.start}T00:00:00`);
    
        const end = new Date(start);
        
        end.setDate(start.getDate() + days.length - 1);
        
        option.textContent =`Week ${week.week} · ${formatDateFull(start)} – ${formatDateFull(end)}`;

        weekFilter.appendChild(option);});

    if (selectedWeekIndex >= weeks.length) selectedWeekIndex = 0;
    weekFilter.value = selectedWeekIndex;
    updateWeekDisplay();
}

function loadCampuses() {
    if (!campusFilter) return;

    campusFilter.innerHTML = '<option value="all">All Campuses</option>';

    if (typeof campuses !== "undefined" && Array.isArray(campuses)) {
        campuses.forEach(campus => {
            const option = document.createElement("option");
            option.value = campus.campus_id;
            option.textContent = campus.campus_name || campus.campus_id;
            campusFilter.appendChild(option);
        });
        return;
    }

    const fallback = [...new Set(
        scheduleData.map(session => session.room_campus_id).filter(Boolean)
    )].sort();

    fallback.forEach(campusId => {
        const option = document.createElement("option");
        option.value = campusId;
        option.textContent = campusId;
        campusFilter.appendChild(option);
    });
}

function getModules() {
    return [...new Set(
        scheduleData
            .map(session => String(session.module_name || "").trim())
            .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b));
}

function showModuleResults(showAll = false) {
    if (!moduleResults || !moduleSearch) return;

    const query = showAll
        ? ""
        : cleanText(moduleSearch.value);

    const modules = getModules().filter(
        module =>
            query === "" ||
            cleanText(module).includes(query)
    );

    moduleResults.innerHTML = "";

    if (modules.length === 0) {
        moduleResults.innerHTML =
            `<div class="no-results">No modules found</div>`;
    } else {
        modules.forEach(module => {
            const result =
                document.createElement("button");

            result.type = "button";
            result.className = "module-result";
            result.textContent = module;

            result.addEventListener(
                "click",
                function () {
                    selectedModule = module;
                    moduleSearch.value = module;
                    moduleResults.style.display = "none";
                    renderCurrentView();
                }
            );

            moduleResults.appendChild(result);
        });
    }

    moduleResults.style.display = "block";
}
function clearModuleFilter() {
    selectedModule = "all";

    if (moduleSearch) moduleSearch.value = "";
    if (moduleResults) moduleResults.style.display = "none";
}

function getFilteredSchedule() {
    const campus = campusFilter ? campusFilter.value : "all";
    const currentWeek = getCurrentWeek();
    let weekStart = null;
    let weekEnd = null;

    if (currentWeek) {
        weekStart = new Date(`${currentWeek.start}T00:00:00`);
        weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + days.length - 1);
    }

    return scheduleData.filter(session => {
        const sessionQuarter = session.quarter_id || session.quarter;
        const quarterMatch = !selectedQuarter || !sessionQuarter || sessionQuarter === selectedQuarter;

        const campusId = session.room_campus_id || session.campus_id || "";
        const campusMatch = campus === "all" || campusId === campus;

        const moduleMatch =
            selectedModule === "all" ||
            cleanText(session.module_name) === cleanText(selectedModule);

        let weekMatch = true;

        if (session.date && weekStart && weekEnd) {
            const sessionDate = new Date(`${session.date}T00:00:00`);
            weekMatch = sessionDate >= weekStart && sessionDate <= weekEnd;
        }

        return quarterMatch && campusMatch && moduleMatch && weekMatch;
    });
}

function renderWeekTimeColumn() {
    if (!weekTimeColumn) return;

    weekTimeColumn.innerHTML = "";
    weekTimeColumn.style.height = `${(teachingEnd - teachingStart) * hourHeight}px`;

    for (let hour = teachingStart; hour < teachingEnd; hour++) {
        const label = document.createElement("div");
        label.className = "week-time-label";
        label.textContent = `${String(hour).padStart(2, "0")}:00`;
        label.style.height = `${hourHeight}px`;
        weekTimeColumn.appendChild(label);
    }

    const endLabel = document.createElement("div");
    endLabel.className = "week-time-label";
    endLabel.style.position = "absolute";
    endLabel.style.bottom = "0";
    endLabel.style.left = "0";
    endLabel.style.right = "0";
    endLabel.style.height = "18px";
    endLabel.style.borderBottom = "0";
    endLabel.textContent = `${String(teachingEnd).padStart(2, "0")}:00`;
    weekTimeColumn.appendChild(endLabel);
}

function sessionsOverlap(first, second) {
    const firstStart = timeToMinutes(first.start_time);
    const firstEnd = timeToMinutes(getEndTime(first));
    const secondStart = timeToMinutes(second.start_time);
    const secondEnd = timeToMinutes(getEndTime(second));

    return firstStart < secondEnd && secondStart < firstEnd;
}

function calculateOverlapLanes(sessions) {
    const sorted = [...sessions].sort(
        (a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time)
    );

    const groups = [];
    let currentGroup = [];
    let currentEnd = -Infinity;

    sorted.forEach(session => {
        const start = timeToMinutes(session.start_time);
        const end = timeToMinutes(getEndTime(session));

        if (currentGroup.length && start >= currentEnd) {
            groups.push(currentGroup);
            currentGroup = [];
            currentEnd = -Infinity;
        }

        currentGroup.push(session);
        currentEnd = Math.max(currentEnd, end);
    });

    if (currentGroup.length) groups.push(currentGroup);

    const positioned = [];

    groups.forEach(group => {
        const lanes = [];

        group.forEach(session => {
            let laneIndex = 0;

            while (true) {
                if (!lanes[laneIndex]) lanes[laneIndex] = [];

                const conflict = lanes[laneIndex].some(
                    existing => sessionsOverlap(session, existing)
                );

                if (!conflict) {
                    lanes[laneIndex].push(session);
                    positioned.push({
                        session,
                        lane: laneIndex,
                        laneCount: 0
                    });
                    break;
                }

                laneIndex++;
            }
        });

        const laneCount = Math.max(lanes.length, 1);

        positioned
            .filter(item => group.includes(item.session))
            .forEach(item => {
                item.laneCount = laneCount;
            });
    });

    return { positioned };
}

function createWeekSessionCard(session) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "week-session-card compact";

    card.innerHTML = `
        <div class="week-session-time">
            <strong>${session.start_time} – ${getEndTime(session)}</strong>
            <span>${session.duration_hours}h</span>
        </div>
        <div class="week-session-title">${session.module_name || "Module"}</div>
        <div class="week-session-meta">${session.room_id || "—"} · ${session.room_campus_id || "—"}</div>
    `;

    card.addEventListener("click", function (event) {
        event.stopPropagation();
        showSessionDetails(session);
    });

    return card;
}

function createMoreButton(day, count) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "more-classes";
    button.textContent = `+ ${count} more ${count === 1 ? "class" : "classes"}`;

    button.addEventListener("click", function (event) {
        event.stopPropagation();
        openDayView(day);
    });

    return button;
}

function renderWeekCalendar() {
    if (!weekCalendarBody) return;

    const sessions = getFilteredSchedule();
    renderWeekTimeColumn();

    document.querySelectorAll(".week-day-column").forEach(column => {
        column.innerHTML = "";
    });

    const currentWeek = getCurrentWeek();
    const sessionCount = document.getElementById("sessionCount");

    if (sessionCount && currentWeek) {
        sessionCount.textContent = `${sessions.length.toLocaleString()} sessions in Week ${currentWeek.week}`;
    }

    const calendarHeight = (teachingEnd - teachingStart) * hourHeight;
    weekCalendarBody.style.height = `${calendarHeight}px`;
    weekCalendarBody.style.minHeight = `${calendarHeight}px`;

    days.forEach(day => {
        const column = document.querySelector(`[data-week-day="${day}"]`);
        if (!column) return;

        const daySessions = sessions
            .filter(session => normaliseDay(session.day) === day)
            .sort((a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time));

        const layer = document.createElement("div");
        layer.className = "week-day-layer";
        layer.style.position = "relative";
        layer.style.width = "100%";
        layer.style.height = `${calendarHeight}px`;

        const grouped = {};

        daySessions.forEach(session => {
            const start = session.start_time;
            if (!grouped[start]) grouped[start] = [];
            grouped[start].push(session);
        });

        const visibleSessions = [];
        let hiddenCount = 0;

        Object.keys(grouped)
            .sort((a, b) => timeToMinutes(a) - timeToMinutes(b))
            .forEach(startTime => {
                const group = grouped[startTime];
                const visible = group.slice(0, previewLimit);
                visibleSessions.push(...visible);

                if (group.length > previewLimit) {
                    hiddenCount += group.length - previewLimit;
                }
            });

        const laneData = calculateOverlapLanes(visibleSessions);

        laneData.positioned.forEach(item => {
            const session = item.session;
            const lane = item.lane;
            const laneCount = Math.max(item.laneCount, 1);
            const card = createWeekSessionCard(session);

            const startMinutes = timeToMinutes(session.start_time);
            const top = ((startMinutes - teachingStart * 60) / 60) * hourHeight;
            const duration = Number(session.duration_hours || 0);
            const cardHeight = Math.max(duration * hourHeight - 8, 62);
            const laneWidth = 100 / laneCount;
            const gap = 6;

            card.style.position = "absolute";
            card.style.top = `${top + 4}px`;
            card.style.left = `calc(${lane * laneWidth}% + ${gap / 2}px)`;
            card.style.width = `calc(${laneWidth}% - ${gap}px)`;
            card.style.height = `${cardHeight}px`;
            card.style.zIndex = "2";

            layer.appendChild(card);
        });

        if (hiddenCount > 0) {
            const more = createMoreButton(day, hiddenCount);
            more.style.position = "absolute";
            more.style.left = "8px";
            more.style.bottom = "8px";
            more.style.zIndex = "30";
            layer.appendChild(more);
        }

        column.appendChild(layer);
    });

    if (sessions.length === 0) {
        weekCalendarBody.classList.add("empty-week");
    } else {
        weekCalendarBody.classList.remove("empty-week");
    }
}

function getDaySessions(day) {
    return getFilteredSchedule()
        .filter(session => normaliseDay(session.day) === day)
        .sort((a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time));
}

function calculateDayLanes(sessions) {
    const lanes = [];
    const positionedSessions = [];

    sessions.forEach(session => {
        let laneIndex = 0;

        while (true) {
            if (!lanes[laneIndex]) lanes[laneIndex] = [];

            const conflict = lanes[laneIndex].some(
                existing => sessionsOverlap(session, existing)
            );

            if (!conflict) {
                lanes[laneIndex].push(session);
                positionedSessions.push({
                    session,
                    lane: laneIndex
                });
                break;
            }

            laneIndex++;
        }
    });

    return {
        positionedSessions,
        laneCount: Math.max(lanes.length, 1)
    };
}

function createDaySessionCard(session) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "day-session-card";

    card.innerHTML = `
        <div class="day-session-top">
            <strong>${session.start_time} – ${getEndTime(session)}</strong>
            <span>${session.duration_hours}h</span>
        </div>
        <div class="day-session-title">${session.module_name || "Module"}</div>
        <div class="day-session-programme">${session.programme_name || ""}</div>
        <div class="day-session-meta">
            <span>${session.room_id || "—"}</span>
            <span>${session.room_campus_id || "—"}</span>
            <span>${session.student_count || 0} students</span>
        </div>
    `;

    card.addEventListener("click", function () {
        showSessionDetails(session);
    });

    return card;
}

function renderDayView() {
    if (!dayDetailContent) return;

    const sessions = getDaySessions(selectedDay);
    const date = getDayDate(selectedDay);
    if (!date) return;

    const dayDetailTitle = document.getElementById("dayDetailTitle");
    const dayDetailDate = document.getElementById("dayDetailDate");
    const dayTeachingHoursDisplay = document.getElementById("dayTeachingHoursDisplay");

    if (dayDetailTitle) dayDetailTitle.textContent = selectedDay;
    if (dayDetailDate) dayDetailDate.textContent = formatDateFull(date);

    if (dayTeachingHoursDisplay) {
        dayTeachingHoursDisplay.textContent =
            `${scheduleConfig.teaching_start} – ${scheduleConfig.teaching_end}`;
    }

    dayDetailContent.innerHTML = "";

    if (sessions.length === 0) {
        dayDetailContent.style.display = "none";
        if (dayEmptyState) dayEmptyState.style.display = "flex";
        return;
    }

    dayDetailContent.style.display = "block";
    if (dayEmptyState) dayEmptyState.style.display = "none";

    const timeline = document.createElement("div");
    timeline.className = "day-horizontal-calendar";

    const timeColumn = document.createElement("div");
    timeColumn.className = "day-calendar-time-column";

    const timeHeader = document.createElement("div");
    timeHeader.className = "day-calendar-time-header";
    timeHeader.textContent = "Time";
    timeColumn.appendChild(timeHeader);

    for (let hour = teachingStart; hour < teachingEnd; hour++) {
        const label = document.createElement("div");
        label.className = "day-calendar-time-label";
        label.textContent = `${String(hour).padStart(2, "0")}:00`;
        timeColumn.appendChild(label);
    }

    const endLabel = document.createElement("div");
    endLabel.className = "day-calendar-time-label day-calendar-end-label";
    endLabel.textContent = `${String(teachingEnd).padStart(2, "0")}:00`;
    timeColumn.appendChild(endLabel);

    const scrollArea = document.createElement("div");
    scrollArea.className = "day-calendar-scroll";

    const track = document.createElement("div");
    track.className = "day-calendar-track";

    const laneData = calculateDayLanes(sessions);
    const laneCount = Math.max(laneData.laneCount, 1);
    const trackWidth = Math.max(laneCount * dayLaneWidth, 700);
    const trackHeight = (teachingEnd - teachingStart) * hourHeight;

    track.style.width = `${trackWidth}px`;
    track.style.height = `${trackHeight}px`;

    for (let hour = teachingStart; hour < teachingEnd; hour++) {
        const line = document.createElement("div");
        line.className = "day-calendar-hour-line";
        line.style.top = `${(hour - teachingStart) * hourHeight}px`;
        track.appendChild(line);
    }

    for (let minute = teachingStart * 60 + 30; minute < teachingEnd * 60; minute += 60) {
        const halfLine = document.createElement("div");
        halfLine.className = "day-calendar-half-line";
        halfLine.style.top = `${((minute - teachingStart * 60) / 60) * hourHeight}px`;
        track.appendChild(halfLine);
    }

    laneData.positionedSessions.forEach(item => {
        const session = item.session;
        const startMinutes = timeToMinutes(session.start_time);
        const durationMinutes = Number(session.duration_hours || 0) * 60;
        const top = ((startMinutes - teachingStart * 60) / 60) * hourHeight;
        const height = (durationMinutes / 60) * hourHeight;
        const left = item.lane * dayLaneWidth;
        const card = createDaySessionCard(session);

        card.style.position = "absolute";
        card.style.top = `${top + 4}px`;
        card.style.left = `${left + 4}px`;
        card.style.width = `${dayLaneWidth - dayLaneGap}px`;
        card.style.height = `${Math.max(height - 8, 70)}px`;

        track.appendChild(card);
    });

    scrollArea.appendChild(track);
    timeline.appendChild(timeColumn);
    timeline.appendChild(scrollArea);
    dayDetailContent.appendChild(timeline);
}

function openDayView(day) {
    selectedDay = day;
    currentView = "day";

    if (weekView) weekView.style.display = "none";
    if (dayView) dayView.style.display = "block";

    renderDayView();

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

function returnToWeekView() {
    currentView = "week";

    if (dayView) dayView.style.display = "none";
    if (weekView) weekView.style.display = "block";

    renderWeekCalendar();

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

document.querySelectorAll(".week-day-header").forEach(header => {
    header.addEventListener("click", function () {
        openDayView(header.dataset.day);
    });
});

const backToWeek = document.getElementById("backToWeek");

if (backToWeek) {
    backToWeek.addEventListener("click", returnToWeekView);
}

const previousDay = document.getElementById("previousDay");
const nextDay = document.getElementById("nextDay");

if (previousDay) {
    previousDay.addEventListener("click", function () {
        const index = days.indexOf(selectedDay);

        if (index > 0) {
            selectedDay = days[index - 1];
            renderDayView();
        }
    });
}

if (nextDay) {
    nextDay.addEventListener("click", function () {
        const index = days.indexOf(selectedDay);

        if (index >= 0 && index < days.length - 1) {
            selectedDay = days[index + 1];
            renderDayView();
        }
    });
}

function showSessionDetails(session) {
    const modalModule = document.getElementById("modalModule");
    const modalClass = document.getElementById("modalClass");
    const modalProgramme = document.getElementById("modalProgramme");
    const modalProfessor = document.getElementById("modalProfessor");
    const modalStudents = document.getElementById("modalStudents");
    const modalRoom = document.getElementById("modalRoom");
    const modalCapacity = document.getElementById("modalCapacity");
    const modalCampus = document.getElementById("modalCampus");
    const modalSchedule = document.getElementById("modalSchedule");
    const modalDuration = document.getElementById("modalDuration");

    if (modalModule) modalModule.textContent = session.module_name || "Module";

    if (modalClass) {
        modalClass.textContent = `Class ${session.class_id || "—"}`;
    }

    if (modalProgramme) {
        modalProgramme.textContent = session.programme_name || "Programme";
    }

    if (modalProfessor) {
        modalProfessor.textContent = session.professor_name || session.professor_id || "—";
    }

    if (modalStudents) {
        modalStudents.textContent = `${session.student_count || 0} students`;
    }

    if (modalRoom) modalRoom.textContent = session.room_id || "—";

    if (modalCapacity) {
        modalCapacity.textContent = session.capacity ? `${session.capacity} seats` : "—";
    }

    if (modalCampus) modalCampus.textContent = session.room_campus_id || "—";

    if (modalSchedule) {
        modalSchedule.textContent =
            `${normaliseDay(session.day)} · ${session.start_time} – ${getEndTime(session)}`;
    }

    if (modalDuration) {
        modalDuration.textContent = `${session.duration_hours} hours`;
    }

    if (sessionModal) {
        sessionModal.classList.add("open");
        sessionModal.setAttribute("aria-hidden", "false");
    }
}

function closeSessionModal() {
    if (!sessionModal) return;

    sessionModal.classList.remove("open");
    sessionModal.setAttribute("aria-hidden", "true");
}

if (sessionModalClose) {
    sessionModalClose.addEventListener("click", closeSessionModal);
}

if (sessionModalDone) {
    sessionModalDone.addEventListener("click", closeSessionModal);
}

if (sessionModalBackdrop) {
    sessionModalBackdrop.addEventListener("click", closeSessionModal);
}

document.addEventListener("keydown", function (event) {
    if (
        event.key === "Escape" &&
        sessionModal &&
        sessionModal.classList.contains("open")
    ) {
        closeSessionModal();
    }
});

function changeWeek(direction) {
    const weeks = calendarWeeks[selectedQuarter] || [];
    const newIndex = selectedWeekIndex + direction;

    if (newIndex < 0 || newIndex >= weeks.length) return;

    selectedWeekIndex = newIndex;

    if (weekFilter) weekFilter.value = selectedWeekIndex;
    renderCurrentView();
}

const previousWeek = document.getElementById("previousWeek");
const nextWeek = document.getElementById("nextWeek");
const previousWeekBottom = document.getElementById("previousWeekBottom");
const nextWeekBottom = document.getElementById("nextWeekBottom");

if (previousWeek) {
    previousWeek.addEventListener("click", function () {
        changeWeek(-1);
    });
}

if (nextWeek) {
    nextWeek.addEventListener("click", function () {
        changeWeek(1);
    });
}

if (previousWeekBottom) {
    previousWeekBottom.addEventListener("click", function () {
        changeWeek(-1);
    });
}

if (nextWeekBottom) {
    nextWeekBottom.addEventListener("click", function () {
        changeWeek(1);
    });
}

const todayWeek = document.getElementById("todayWeek");

if (todayWeek) {
    todayWeek.addEventListener("click", function () {
        selectedWeekIndex = 0;

        if (weekFilter) weekFilter.value = 0;
        renderCurrentView();
    });
}

if (quarterFilter) {
    quarterFilter.addEventListener("change", function () {
        selectedQuarter = quarterFilter.value;
        selectedWeekIndex = 0;
        selectedDay = days[0] || "Monday";

        clearModuleFilter();
        loadWeeks();
        renderCurrentView();
    });
}

if (weekFilter) {
    weekFilter.addEventListener("change", function () {
        selectedWeekIndex = parseInt(weekFilter.value, 10);
        renderCurrentView();
    });
}

if (campusFilter) {
    campusFilter.addEventListener("change", function () {
        clearModuleFilter();
        renderCurrentView();
    });
}

if (moduleSearch) {
    moduleSearch.addEventListener("input", function () {
        selectedModule = "all";
        showModuleResults();
    });
}

if (moduleDropdown) {
    moduleDropdown.addEventListener("click", function (event) {
        event.stopPropagation();

        if (moduleResults && moduleResults.style.display === "block") {
            moduleResults.style.display = "none";
        } else {
            showModuleResults(true);
            if (moduleSearch) moduleSearch.focus();
        }
    });
}

document.addEventListener("click", function (event) {
    if (!event.target.closest(".module-select")) {
        if (moduleResults) moduleResults.style.display = "none";
    }
});

function renderCurrentView() {
    updateWeekDisplay();

    if (currentView === "day") {
        renderDayView();
    } else {
        renderWeekCalendar();
    }
}

loadCampuses();
loadWeeks();
renderCurrentView();