console.log("UniPlan timetable loaded");


/* =========================================================
   STATE
   ========================================================= */

let selectedQuarter = "Q1";
let selectedWeekIndex = 0;
let selectedModule = "all";
let selectedDay = "Monday";
let currentView = "week";


/* =========================================================
   CONSTANTS
   ========================================================= */

const days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
];

const teachingStart = 9;
const teachingEnd = 17;

/*
    One hour in the timetable = 72px.
    09:00 -> 17:00 = 8 hours = 576px.
*/
const hourHeight = 72;

/*
    In the week overview we show at most
    two classes for the same start time.
*/
const previewLimit = 2;

/*
    Width of a lane in detailed day view.
*/
const dayLaneWidth = 190;

const dayLaneGap = 8;


/* =========================================================
   ELEMENTS
   ========================================================= */

const quarterFilter =
    document.getElementById("quarterFilter");

const weekFilter =
    document.getElementById("weekFilter");

const campusFilter =
    document.getElementById("campusFilter");

const moduleSearch =
    document.getElementById("moduleSearch");

const moduleDropdown =
    document.getElementById("moduleDropdown");

const moduleResults =
    document.getElementById("moduleResults");

const weekView =
    document.getElementById("weekView");

const dayView =
    document.getElementById("dayView");

const weekCalendarBody =
    document.getElementById("weekCalendarBody");

const weekTimeColumn =
    document.getElementById("weekTimeColumn");

const dayDetailContent =
    document.getElementById("dayDetailContent");

const dayEmptyState =
    document.getElementById("dayEmptyState");


/* =========================================================
   MODAL
   ========================================================= */

const sessionModal =
    document.getElementById("sessionModal");

const sessionModalClose =
    document.getElementById("sessionModalClose");

const sessionModalDone =
    document.getElementById("sessionModalDone");

const sessionModalBackdrop =
    document.getElementById("sessionModalBackdrop");


/* =========================================================
   HELPERS
   ========================================================= */

function cleanText(value) {

    return String(value || "")
        .trim()
        .toLowerCase();

}


function timeToMinutes(time) {

    const parts =
        String(time).split(":");

    return (
        parseInt(parts[0], 10) * 60 +
        parseInt(parts[1], 10)
    );

}


function minutesToTime(minutes) {

    const hours =
        Math.floor(minutes / 60);

    const mins =
        minutes % 60;

    return (
        String(hours).padStart(2, "0") +
        ":" +
        String(mins).padStart(2, "0")
    );

}


function getEndTime(session) {

    const start =
        timeToMinutes(
            session.start_time
        );

    const duration =
        Number(
            session.duration_hours
        ) * 60;

    return minutesToTime(
        start + duration
    );

}


function formatDateFull(date) {

    return date.toLocaleDateString(
        "en-GB",
        {
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    );

}


function formatDateShort(date) {

    return date.toLocaleDateString(
        "en-GB",
        {
            day: "2-digit",
            month: "short"
        }
    );

}


/* =========================================================
   WEEK HELPERS
   ========================================================= */

function getCurrentWeek() {

    const weeks =
        calendarWeeks[
            selectedQuarter
        ] || [];

    return (
        weeks[
            selectedWeekIndex
        ] || null
    );

}


function getDayDate(day) {

    const week =
        getCurrentWeek();

    if (!week) {
        return null;
    }

    const startDate =
        new Date(
            `${week.start}T00:00:00`
        );

    const dayIndex =
        days.indexOf(day);

    const date =
        new Date(startDate);

    date.setDate(
        startDate.getDate() +
        dayIndex
    );

    return date;

}


/* =========================================================
   WEEK DISPLAY
   ========================================================= */

function updateWeekDisplay() {

    const week =
        getCurrentWeek();

    if (!week) {
        return;
    }


    const weekTitle =
        document.getElementById(
            "weekTitle"
        );

    const weekRange =
        document.getElementById(
            "weekRange"
        );

    const monthYear =
        document.getElementById(
            "monthYear"
        );


    if (weekTitle) {

        weekTitle.textContent =
            `Week ${week.week}`;

    }


    if (weekRange) {

        weekRange.textContent =
            `${week.start_display} – ${week.end_display}`;

    }


    if (monthYear) {

        const startDate =
            new Date(
                `${week.start}T00:00:00`
            );

        monthYear.textContent =
            startDate.toLocaleDateString(
                "en-GB",
                {
                    month: "long",
                    year: "numeric"
                }
            );

    }


    document
        .querySelectorAll(
            ".week-day-header"
        )
        .forEach(
            header => {

                const day =
                    header.dataset.day;

                const date =
                    getDayDate(day);

                const dateElement =
                    header.querySelector(
                        "[data-day-date]"
                    );

                if (
                    date &&
                    dateElement
                ) {

                    dateElement.textContent =
                        formatDateShort(date);

                }

            }
        );

}


/* =========================================================
   LOAD WEEKS
   ========================================================= */

function loadWeeks() {

    if (!weekFilter) {
        return;
    }


    const weeks =
        calendarWeeks[
            selectedQuarter
        ] || [];


    weekFilter.innerHTML =
        "";


    weeks.forEach(
        (week, index) => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                index;

            option.textContent =
                `Week ${week.week} · ` +
                `${week.start_display} – ` +
                `${week.end_display}`;

            weekFilter.appendChild(
                option
            );

        }
    );


    if (
        selectedWeekIndex >=
        weeks.length
    ) {

        selectedWeekIndex = 0;

    }


    weekFilter.value =
        selectedWeekIndex;


    updateWeekDisplay();

}


/* =========================================================
   LOAD CAMPUSES
   ========================================================= */

function loadCampuses() {

    if (!campusFilter) {
        return;
    }


    const campuses = [
        ...new Set(
            scheduleData
                .map(
                    session =>
                        session.room_campus_id
                )
                .filter(Boolean)
        )
    ].sort();


    campusFilter.innerHTML = `
        <option value="all">
            All Campuses
        </option>
    `;


    campuses.forEach(
        campus => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                campus;

            option.textContent =
                campus;

            campusFilter.appendChild(
                option
            );

        }
    );

}


/* =========================================================
   MODULE SEARCH
   ========================================================= */

function getModules() {

    const modules =
        scheduleData
            .map(
                session =>
                    String(
                        session.module_name || ""
                    ).trim()
            )
            .filter(Boolean);


    return [
        ...new Set(modules)
    ].sort(
        (a, b) =>
            a.localeCompare(b)
    );

}


function showModuleResults() {

    if (
        !moduleSearch ||
        !moduleResults
    ) {
        return;
    }


    const query =
        cleanText(
            moduleSearch.value
        );


    moduleResults.innerHTML =
        "";


    let modules =
        getModules();


    if (
        query !== ""
    ) {

        modules =
            modules.filter(
                module =>
                    cleanText(
                        module
                    ).includes(query)
            );

    }


    if (
        modules.length === 0
    ) {

        moduleResults.innerHTML = `
            <div class="no-results">
                No modules found
            </div>
        `;

    } else {

        modules.forEach(
            module => {

                const result =
                    document.createElement(
                        "div"
                    );

                result.className =
                    "search-result";

                result.textContent =
                    module;


                result.addEventListener(
                    "click",
                    function() {

                        selectedModule =
                            module;

                        moduleSearch.value =
                            module;

                        moduleResults.style.display =
                            "none";

                        renderCurrentView();

                    }
                );


                moduleResults.appendChild(
                    result
                );

            }
        );

    }


    moduleResults.style.display =
        "block";

}


function clearModuleFilter() {

    selectedModule =
        "all";


    if (moduleSearch) {

        moduleSearch.value =
            "";

    }

}


/* =========================================================
   FILTER SCHEDULE
   ========================================================= */

function getFilteredSchedule() {

    const campus =
        campusFilter
            ? campusFilter.value
            : "all";


    return scheduleData.filter(
        session => {

            const quarterMatch =
                session.quarter_id ===
                selectedQuarter;


            const campusMatch =
                campus === "all" ||
                session.room_campus_id ===
                campus;


            const moduleMatch =
                selectedModule === "all" ||
                cleanText(
                    session.module_name
                ) ===
                cleanText(
                    selectedModule
                );


            return (
                quarterMatch &&
                campusMatch &&
                moduleMatch
            );

        }
    );

}


/* =========================================================
   WEEK TIME COLUMN
   ========================================================= */

function renderWeekTimeColumn() {

    if (!weekTimeColumn) {
        return;
    }


    weekTimeColumn.innerHTML =
        "";


    weekTimeColumn.style.position =
        "relative";


    weekTimeColumn.style.height =
        `${(
            teachingEnd -
            teachingStart
        ) * hourHeight}px`;


    /*
        09:00 through 16:00
    */

    for (
        let hour = teachingStart;
        hour < teachingEnd;
        hour++
    ) {

        const label =
            document.createElement(
                "div"
            );

        label.className =
            "week-time-label";

        label.textContent =
            `${String(
                hour
            ).padStart(2, "0")}:00`;

        label.style.height =
            `${hourHeight}px`;

        label.style.boxSizing =
            "border-box";

        weekTimeColumn.appendChild(
            label
        );

    }


    /*
        17:00 is the bottom boundary.
    */

    const endLabel =
        document.createElement(
            "div"
        );

    endLabel.className =
        "week-time-label";

    endLabel.textContent =
        "17:00";

    endLabel.style.position =
        "absolute";

    endLabel.style.left =
        "0";

    endLabel.style.right =
        "0";

    endLabel.style.bottom =
        "-1px";

    endLabel.style.height =
        "20px";

    endLabel.style.paddingTop =
        "2px";

    endLabel.style.boxSizing =
        "border-box";

    weekTimeColumn.appendChild(
        endLabel
    );

}


/* =========================================================
   WEEK SESSION CARD
   ========================================================= */

function createWeekSessionCard(
    session
) {

    const card =
        document.createElement(
            "button"
        );


    card.type =
        "button";


    card.className =
        "week-session-card compact";


    card.innerHTML = `

        <div class="week-session-time">

            <strong>
                ${session.start_time}
                –
                ${getEndTime(session)}
            </strong>

            <span>
                ${session.duration_hours}h
            </span>

        </div>


        <div class="week-session-title">
            ${session.module_name}
        </div>


        <div class="week-session-meta">
            ${session.room_id || "—"}
            ·
            ${session.room_campus_id || "—"}
        </div>

    `;


    card.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            showSessionDetails(
                session
            );

        }
    );


    return card;

}


/* =========================================================
   MORE CLASSES BUTTON
   ========================================================= */

function createMoreButton(
    day,
    count
) {

    const button =
        document.createElement(
            "button"
        );


    button.type =
        "button";


    button.className =
        "more-classes";


    button.textContent =
        `+ ${count} more ${
            count === 1
                ? "class"
                : "classes"
        }`;


    button.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            openDayView(
                day
            );

        }
    );


    return button;

}


/* =========================================================
   OVERLAP CHECK
   ========================================================= */

function sessionsOverlap(
    first,
    second
) {

    const firstStart =
        timeToMinutes(
            first.start_time
        );

    const firstEnd =
        timeToMinutes(
            getEndTime(first)
        );


    const secondStart =
        timeToMinutes(
            second.start_time
        );

    const secondEnd =
        timeToMinutes(
            getEndTime(second)
        );


    return (
        firstStart < secondEnd &&
        secondStart < firstEnd
    );

}


/* =========================================================
   FIND OVERLAP GROUPS
   ========================================================= */

/*
    This is the important visual fix.

    We do NOT calculate one lane count for the
    entire day.

    Instead, we create separate groups of
    sessions that actually overlap.

    Example:

        09:00–11:00 A
        09:00–11:00 B

    => A and B share 2 lanes.

        14:00–16:00 C

    => C is completely independent and gets
       the full width again.
*/

function buildOverlapGroups(
    sessions
) {

    const sorted =
        [...sessions].sort(
            (a, b) =>
                timeToMinutes(
                    a.start_time
                )
                -
                timeToMinutes(
                    b.start_time
                )
        );


    const groups = [];


    sorted.forEach(
        session => {

            let placed =
                false;


            for (
                let groupIndex = 0;
                groupIndex < groups.length;
                groupIndex++
            ) {

                const group =
                    groups[groupIndex];


                const overlaps =
                    group.some(
                        existing =>
                            sessionsOverlap(
                                session,
                                existing
                            )
                    );


                if (overlaps) {

                    group.push(
                        session
                    );

                    placed = true;

                    break;

                }

            }


            if (!placed) {

                groups.push(
                    [session]
                );

            }

        }
    );


    return groups;

}


/* =========================================================
   CALCULATE LANES FOR ONE OVERLAP GROUP
   ========================================================= */

function calculateGroupLanes(
    sessions
) {

    const sorted =
        [...sessions].sort(
            (a, b) =>
                timeToMinutes(
                    a.start_time
                )
                -
                timeToMinutes(
                    b.start_time
                )
        );


    const lanes = [];


    const positioned = [];


    sorted.forEach(
        session => {

            let laneIndex = 0;


            while (true) {

                if (
                    !lanes[laneIndex]
                ) {

                    lanes[laneIndex] =
                        [];

                }


                const lane =
                    lanes[laneIndex];


                const conflict =
                    lane.some(
                        existing =>
                            sessionsOverlap(
                                session,
                                existing
                            )
                    );


                if (!conflict) {

                    lane.push(
                        session
                    );


                    positioned.push(
                        {
                            session:
                                session,

                            lane:
                                laneIndex
                        }
                    );


                    break;

                }


                laneIndex++;

            }

        }
    );


    return {
        positioned,
        laneCount:
            lanes.length
    };

}


/* =========================================================
   WEEK CALENDAR
   ========================================================= */

   function renderWeekCalendar() {

    if (!weekCalendarBody) {
        return;
    }


    const sessions =
        getFilteredSchedule();


    renderWeekTimeColumn();


    /*
        ------------------------------------------------
        CLEAR PREVIOUS WEEK CONTENT
        ------------------------------------------------
    */

    document
        .querySelectorAll(
            ".week-day-column"
        )
        .forEach(
            column => {

                column.innerHTML =
                    "";

            }
        );


    /*
        ------------------------------------------------
        WEEK INFORMATION
        ------------------------------------------------
    */

    const currentWeek =
        getCurrentWeek();


    const sessionCount =
        document.getElementById(
            "sessionCount"
        );


    if (
        sessionCount &&
        currentWeek
    ) {

        sessionCount.textContent =
            `${sessions.length.toLocaleString()} ` +
            `sessions in Week ${currentWeek.week}`;

    }


    /*
        ------------------------------------------------
        CALENDAR HEIGHT
        ------------------------------------------------

        09:00 → 17:00
        8 hours × 72px
        = 576px
        ------------------------------------------------
    */

    const calendarHeight =
        (
            teachingEnd -
            teachingStart
        ) * hourHeight;


    weekCalendarBody.style.height =
        `${calendarHeight}px`;


    weekCalendarBody.style.minHeight =
        `${calendarHeight}px`;


    /*
        ------------------------------------------------
        WEEK PREVIEW RULE

        Exactly TWO horizontal lanes per day.

        The lanes continue throughout the entire
        09:00–17:00 timeline.

        A new class reuses a lane as soon as that
        lane becomes free.

        This gives the timetable a consistent shape.
        ------------------------------------------------
    */

    const previewLaneCount =
        2;


    const laneGap =
        8;


    /*
        ------------------------------------------------
        RENDER MONDAY → FRIDAY
        ------------------------------------------------
    */

    days.forEach(
        day => {

            const column =
                document.querySelector(
                    `[data-week-day="${day}"]`
                );


            if (
                !column
            ) {
                return;
            }


            /*
                Get every session for this day.
            */

            const daySessions =
                sessions
                    .filter(
                        session =>
                            session.day ===
                            day
                    )
                    .sort(
                        (a, b) => {

                            const startDifference =
                                timeToMinutes(
                                    a.start_time
                                )
                                -
                                timeToMinutes(
                                    b.start_time
                                );


                            if (
                                startDifference !== 0
                            ) {

                                return startDifference;

                            }


                            /*
                                For classes with the same
                                start time, larger classes
                                are shown first.
                            */

                            return (
                                Number(
                                    b.student_count || 0
                                )
                                -
                                Number(
                                    a.student_count || 0
                                )
                            );

                        }
                    );


            /*
                ------------------------------------------------
                DAY LAYER
                ------------------------------------------------
            */

            const layer =
                document.createElement(
                    "div"
                );


            layer.className =
                "week-day-layer";


            layer.style.position =
                "relative";


            layer.style.width =
                "100%";


            layer.style.height =
                `${calendarHeight}px`;


            layer.style.overflow =
                "hidden";


            /*
                ------------------------------------------------
                LANE STATE

                Each lane stores the ending time of
                the class currently occupying it.
                ------------------------------------------------
            */

            const laneEndTimes =
                Array(
                    previewLaneCount
                ).fill(
                    teachingStart * 60
                );


            /*
                ------------------------------------------------
                HIDDEN COUNT

                Any class that cannot fit into one of
                the two visible lanes is counted here.
                ------------------------------------------------
            */

            let hiddenCount =
                0;


            /*
                ------------------------------------------------
                RENDER SESSIONS
                ------------------------------------------------
            */

            daySessions.forEach(
                session => {

                    const start =
                        timeToMinutes(
                            session.start_time
                        );


                    const end =
                        timeToMinutes(
                            getEndTime(
                                session
                            )
                        );


                    /*
                        Find the first lane which has
                        become free.

                        A class ending at 11:00 allows
                        another class beginning at 11:00
                        to use the same lane.
                    */

                    let laneIndex =
                        -1;


                    for (
                        let lane = 0;
                        lane < previewLaneCount;
                        lane++
                    ) {

                        if (
                            laneEndTimes[lane] <=
                            start
                        ) {

                            laneIndex =
                                lane;

                            break;

                        }

                    }


                    /*
                        No lane available.

                        Keep the actual schedule untouched,
                        but hide this class from the Week
                        Preview and count it for the
                        "+ X more classes" button.
                    */

                    if (
                        laneIndex === -1
                    ) {

                        hiddenCount +=
                            1;

                        return;

                    }


                    /*
                        The lane is now occupied until
                        this class ends.
                    */

                    laneEndTimes[laneIndex] =
                        end;


                    /*
                        ------------------------------------------------
                        CREATE CARD
                        ------------------------------------------------
                    */

                    const card =
                        createWeekSessionCard(
                            session
                        );


                    /*
                        ------------------------------------------------
                        VERTICAL POSITION
                        ------------------------------------------------
                    */

                    const top =
                        (
                            start -
                            teachingStart * 60
                        )
                        /
                        60
                        *
                        hourHeight;


                    /*
                        Height represents REAL duration.

                        2h   = 144px
                        2.5h = 180px
                        3h   = 216px
                    */

                    const duration =
                        Number(
                            session.duration_hours
                        );


                    const cardHeight =
                        duration *
                        hourHeight;


                    /*
                        ------------------------------------------------
                        HORIZONTAL POSITION

                        Exactly TWO equal lanes.

                        Lane 0 = left half
                        Lane 1 = right half
                        ------------------------------------------------
                    */

                    const laneWidth =
                        100 /
                        previewLaneCount;


                    const left =
                        laneIndex *
                        laneWidth;


                    /*
                        ------------------------------------------------
                        CARD POSITIONING
                        ------------------------------------------------
                    */

                    card.style.position =
                        "absolute";


                    card.style.top =
                        `${top + 4}px`;


                    card.style.left =
                        `calc(${left}% + ${laneGap / 2}px)`;


                    card.style.width =
                        `calc(${laneWidth}% - ${laneGap}px)`;


                    card.style.height =
                        `${Math.max(
                            cardHeight - 8,
                            70
                        )}px`;


                    card.style.boxSizing =
                        "border-box";


                    card.style.zIndex =
                        "2";


                    /*
                        Add the card to the day.
                    */

                    layer.appendChild(
                        card
                    );

                }
            );


            /*
                ------------------------------------------------
                MORE CLASSES BUTTON
                ------------------------------------------------

                This button represents every class
                hidden because the two preview lanes
                were already occupied.
            */

            if (
                hiddenCount > 0
            ) {

                const more =
                    createMoreButton(
                        day,
                        hiddenCount
                    );


                more.style.position =
                    "absolute";


                more.style.left =
                    "8px";


                more.style.bottom =
                    "8px";


                more.style.zIndex =
                    "40";


                layer.appendChild(
                    more
                );

            }


            /*
                Add the finished layer to the day column.
            */

            column.appendChild(
                layer
            );

        }
    );


    /*
        ------------------------------------------------
        EMPTY STATE
        ------------------------------------------------
    */

    if (
        sessions.length === 0
    ) {

        weekCalendarBody.classList.add(
            "empty-week"
        );

    } else {

        weekCalendarBody.classList.remove(
            "empty-week"
        );

    }

}
/* =========================================================
   DAY SESSIONS
   ========================================================= */

function getDaySessions(
    day
) {

    return getFilteredSchedule()
        .filter(
            session =>
                session.day === day
        )
        .sort(
            (a, b) =>
                timeToMinutes(
                    a.start_time
                )
                -
                timeToMinutes(
                    b.start_time
                )
        );

}


/* =========================================================
   DAY VIEW LANES
   ========================================================= */

function calculateDayLanes(
    sessions
) {

    const lanes = [];

    const positionedSessions = [];


    sessions.forEach(
        session => {

            const start =
                timeToMinutes(
                    session.start_time
                );


            const end =
                timeToMinutes(
                    getEndTime(session)
                );


            let laneIndex =
                0;


            while (true) {

                if (
                    !lanes[laneIndex]
                ) {

                    lanes[laneIndex] =
                        [];

                }


                const lane =
                    lanes[laneIndex];


                const overlaps =
                    lane.some(
                        existing => {

                            const existingStart =
                                timeToMinutes(
                                    existing.start_time
                                );


                            const existingEnd =
                                timeToMinutes(
                                    getEndTime(
                                        existing
                                    )
                                );


                            return (
                                start <
                                existingEnd
                                &&
                                end >
                                existingStart
                            );

                        }
                    );


                if (!overlaps) {

                    lane.push(
                        session
                    );


                    positionedSessions.push(
                        {
                            session:
                                session,

                            lane:
                                laneIndex
                        }
                    );


                    break;

                }


                laneIndex++;

            }

        }
    );


    return {
        positionedSessions,
        laneCount:
            lanes.length
    };

}


/* =========================================================
   DAY SESSION CARD
   ========================================================= */

function createDaySessionCard(
    session
) {

    const card =
        document.createElement(
            "button"
        );


    card.type =
        "button";


    card.className =
        "day-session-card";


    card.innerHTML = `

        <div class="day-session-top">

            <strong>
                ${session.start_time}
                –
                ${getEndTime(session)}
            </strong>

            <span>
                ${session.duration_hours}h
            </span>

        </div>


        <div class="day-session-title">
            ${session.module_name}
        </div>


        <div class="day-session-programme">
            ${session.programme_name || ""}
        </div>


        <div class="day-session-meta">

            <span>
                ${session.room_id || "—"}
            </span>

            <span>
                ${session.room_campus_id || "—"}
            </span>

            <span>
                ${session.student_count || 0}
                students
            </span>

        </div>

    `;


    card.addEventListener(
        "click",
        function() {

            showSessionDetails(
                session
            );

        }
    );


    return card;

}


/* =========================================================
   DAY VIEW
   ========================================================= */

function renderDayView() {

    if (!dayDetailContent) {
        return;
    }


    const sessions =
        getDaySessions(
            selectedDay
        );


    const date =
        getDayDate(
            selectedDay
        );


    if (!date) {
        return;
    }


    const dayDetailTitle =
        document.getElementById(
            "dayDetailTitle"
        );


    const dayDetailDate =
        document.getElementById(
            "dayDetailDate"
        );


    if (dayDetailTitle) {

        dayDetailTitle.textContent =
            selectedDay;

    }


    if (dayDetailDate) {

        dayDetailDate.textContent =
            formatDateFull(
                date
            );

    }


    dayDetailContent.innerHTML =
        "";


    if (
        sessions.length === 0
    ) {

        dayDetailContent.style.display =
            "none";


        if (dayEmptyState) {

            dayEmptyState.style.display =
                "flex";

        }

        return;

    }


    dayDetailContent.style.display =
        "block";


    if (dayEmptyState) {

        dayEmptyState.style.display =
            "none";

    }


    /* =====================================================
       DAY CALENDAR
       ===================================================== */

    const timeline =
        document.createElement(
            "div"
        );


    timeline.className =
        "day-horizontal-calendar";


    /* =====================================================
       TIME COLUMN
       ===================================================== */

    const timeColumn =
        document.createElement(
            "div"
        );


    timeColumn.className =
        "day-calendar-time-column";


    for (
        let hour = teachingStart;
        hour < teachingEnd;
        hour++
    ) {

        const label =
            document.createElement(
                "div"
            );


        label.className =
            "day-calendar-time-label";


        label.textContent =
            `${String(
                hour
            ).padStart(2, "0")}:00`;


        timeColumn.appendChild(
            label
        );

    }


    /*
        Final 17:00 marker.
    */

    const endLabel =
        document.createElement(
            "div"
        );


    endLabel.className =
        "day-calendar-time-label " +
        "day-calendar-end-label";


    endLabel.textContent =
        "17:00";


    timeColumn.appendChild(
        endLabel
    );


    /* =====================================================
       SCROLL AREA
       ===================================================== */

    const scrollArea =
        document.createElement(
            "div"
        );


    scrollArea.className =
        "day-calendar-scroll";


    const track =
        document.createElement(
            "div"
        );


    track.className =
        "day-calendar-track";


    const laneData =
        calculateDayLanes(
            sessions
        );


    const laneCount =
        Math.max(
            laneData.laneCount,
            1
        );


    const trackWidth =
        Math.max(
            laneCount *
            dayLaneWidth,
            700
        );


    const trackHeight =
        (
            teachingEnd -
            teachingStart
        ) * hourHeight;


    track.style.width =
        `${trackWidth}px`;


    track.style.height =
        `${trackHeight}px`;


    /* =====================================================
       GRID LINES
       ===================================================== */

    for (
        let hour = teachingStart;
        hour < teachingEnd;
        hour++
    ) {

        const line =
            document.createElement(
                "div"
            );


        line.className =
            "day-calendar-hour-line";


        line.style.top =
            `${
                (
                    hour -
                    teachingStart
                ) *
                hourHeight
            }px`;


        track.appendChild(
            line
        );

    }


    /*
        Half-hour lines.
    */

    for (
        let minute =
            teachingStart * 60 + 30;

        minute <
        teachingEnd * 60;

        minute += 60
    ) {

        const halfLine =
            document.createElement(
                "div"
            );


        halfLine.className =
            "day-calendar-half-line";


        halfLine.style.top =
            `${
                (
                    (
                        minute -
                        teachingStart * 60
                    ) /
                    60
                ) *
                hourHeight
            }px`;


        track.appendChild(
            halfLine
        );

    }


    /* =====================================================
       DAY SESSION BLOCKS
       ===================================================== */

    laneData.positionedSessions.forEach(
        item => {

            const session =
                item.session;


            const lane =
                item.lane;


            const card =
                createDaySessionCard(
                    session
                );


            const startMinutes =
                timeToMinutes(
                    session.start_time
                );


            const durationMinutes =
                Number(
                    session.duration_hours
                ) * 60;


            const top =
                (
                    startMinutes -
                    teachingStart * 60
                )
                /
                60
                *
                hourHeight;


            const height =
                (
                    durationMinutes /
                    60
                ) *
                hourHeight;


            const left =
                lane *
                dayLaneWidth;


            card.style.position =
                "absolute";


            card.style.top =
                `${top + 4}px`;


            card.style.left =
                `${left + 4}px`;


            card.style.width =
                `${dayLaneWidth - dayLaneGap}px`;


            card.style.height =
                `${Math.max(
                    height - 8,
                    70
                )}px`;


            card.style.zIndex =
                "5";


            track.appendChild(
                card
            );

        }
    );


    scrollArea.appendChild(
        track
    );


    timeline.appendChild(
        timeColumn
    );


    timeline.appendChild(
        scrollArea
    );


    dayDetailContent.appendChild(
        timeline
    );

}


/* =========================================================
   OPEN DAY VIEW
   ========================================================= */

function openDayView(
    day
) {

    selectedDay =
        day;


    currentView =
        "day";


    if (weekView) {

        weekView.style.display =
            "none";

    }


    if (dayView) {

        dayView.style.display =
            "block";

    }


    renderDayView();


    window.scrollTo(
        {
            top: 0,
            behavior: "smooth"
        }
    );

}


/* =========================================================
   WEEK DAY HEADER CLICK
   ========================================================= */

document
    .querySelectorAll(
        ".week-day-header"
    )
    .forEach(
        header => {

            header.addEventListener(
                "click",
                function() {

                    openDayView(
                        header.dataset.day
                    );

                }
            );

        }
    );


/* =========================================================
   BACK TO WEEK
   ========================================================= */

const backToWeek =
    document.getElementById(
        "backToWeek"
    );


if (backToWeek) {

    backToWeek.addEventListener(
        "click",
        function() {

            currentView =
                "week";


            if (dayView) {

                dayView.style.display =
                    "none";

            }


            if (weekView) {

                weekView.style.display =
                    "block";

            }


            renderWeekCalendar();


            window.scrollTo(
                {
                    top: 0,
                    behavior: "smooth"
                }
            );

        }
    );

}


/* =========================================================
   PREVIOUS DAY
   ========================================================= */

const previousDay =
    document.getElementById(
        "previousDay"
    );


if (previousDay) {

    previousDay.addEventListener(
        "click",
        function() {

            const index =
                days.indexOf(
                    selectedDay
                );


            if (
                index > 0
            ) {

                selectedDay =
                    days[
                        index - 1
                    ];


                renderDayView();

            }

        }
    );

}


/* =========================================================
   NEXT DAY
   ========================================================= */

const nextDay =
    document.getElementById(
        "nextDay"
    );


if (nextDay) {

    nextDay.addEventListener(
        "click",
        function() {

            const index =
                days.indexOf(
                    selectedDay
                );


            if (
                index <
                days.length - 1
            ) {

                selectedDay =
                    days[
                        index + 1
                    ];


                renderDayView();

            }

        }
    );

}


/* =========================================================
   SESSION MODAL
   ========================================================= */

function showSessionDetails(
    session
) {

    const modalModule =
        document.getElementById(
            "modalModule"
        );


    const modalClass =
        document.getElementById(
            "modalClass"
        );


    const modalProgramme =
        document.getElementById(
            "modalProgramme"
        );


    const modalProfessor =
        document.getElementById(
            "modalProfessor"
        );


    const modalStudents =
        document.getElementById(
            "modalStudents"
        );


    const modalRoom =
        document.getElementById(
            "modalRoom"
        );


    const modalCapacity =
        document.getElementById(
            "modalCapacity"
        );


    const modalCampus =
        document.getElementById(
            "modalCampus"
        );


    const modalSchedule =
        document.getElementById(
            "modalSchedule"
        );


    const modalDuration =
        document.getElementById(
            "modalDuration"
        );


    if (modalModule) {

        modalModule.textContent =
            session.module_name ||
            "Module";

    }


    if (modalClass) {

        modalClass.textContent =
            `Class ${
                session.class_id ||
                "—"
            }`;

    }


    if (modalProgramme) {

        modalProgramme.textContent =
            session.programme_name ||
            "Programme";

    }


    /*
        Show real professor name.
        Fall back to ID if somehow
        the name is unavailable.
    */

    if (modalProfessor) {

        modalProfessor.textContent =
            session.professor_name ||
            session.professor_id ||
            "—";

    }


    if (modalStudents) {

        modalStudents.textContent =
            `${
                session.student_count ||
                0
            } students`;

    }


    if (modalRoom) {

        modalRoom.textContent =
            session.room_id ||
            "—";

    }


    if (modalCapacity) {

        modalCapacity.textContent =
            session.capacity
                ? `${session.capacity} seats`
                : "—";

    }


    if (modalCampus) {

        modalCampus.textContent =
            session.room_campus_id ||
            "—";

    }


    /*
        Full timing:

        Monday · 09:00 – 11:00
    */

    if (modalSchedule) {

        modalSchedule.textContent =
            `${session.day} · ` +
            `${session.start_time} – ` +
            `${getEndTime(session)}`;

    }


    if (modalDuration) {

        modalDuration.textContent =
            `${session.duration_hours} hours`;

    }


    if (sessionModal) {

        sessionModal.classList.add(
            "open"
        );


        sessionModal.setAttribute(
            "aria-hidden",
            "false"
        );

    }

}


/* =========================================================
   CLOSE MODAL
   ========================================================= */

function closeSessionModal() {

    if (!sessionModal) {
        return;
    }


    sessionModal.classList.remove(
        "open"
    );


    sessionModal.setAttribute(
        "aria-hidden",
        "true"
    );

}


if (sessionModalClose) {

    sessionModalClose.addEventListener(
        "click",
        closeSessionModal
    );

}


if (sessionModalDone) {

    sessionModalDone.addEventListener(
        "click",
        closeSessionModal
    );

}


if (sessionModalBackdrop) {

    sessionModalBackdrop.addEventListener(
        "click",
        closeSessionModal
    );

}


document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Escape" &&
            sessionModal &&
            sessionModal.classList.contains(
                "open"
            )
        ) {

            closeSessionModal();

        }

    }
);


/* =========================================================
   WEEK NAVIGATION
   ========================================================= */

function changeWeek(
    direction
) {

    const weeks =
        calendarWeeks[
            selectedQuarter
        ] || [];


    const newIndex =
        selectedWeekIndex +
        direction;


    if (
        newIndex < 0 ||
        newIndex >= weeks.length
    ) {

        return;

    }


    selectedWeekIndex =
        newIndex;


    if (weekFilter) {

        weekFilter.value =
            selectedWeekIndex;

    }


    renderCurrentView();

}


/* =========================================================
   WEEK BUTTONS
   ========================================================= */

const previousWeek =
    document.getElementById(
        "previousWeek"
    );


const nextWeek =
    document.getElementById(
        "nextWeek"
    );


const previousWeekBottom =
    document.getElementById(
        "previousWeekBottom"
    );


const nextWeekBottom =
    document.getElementById(
        "nextWeekBottom"
    );


if (previousWeek) {

    previousWeek.addEventListener(
        "click",
        function() {

            changeWeek(-1);

        }
    );

}


if (nextWeek) {

    nextWeek.addEventListener(
        "click",
        function() {

            changeWeek(1);

        }
    );

}


if (previousWeekBottom) {

    previousWeekBottom.addEventListener(
        "click",
        function() {

            changeWeek(-1);

        }
    );

}


if (nextWeekBottom) {

    nextWeekBottom.addEventListener(
        "click",
        function() {

            changeWeek(1);

        }
    );

}


/* =========================================================
   CURRENT WEEK
   ========================================================= */

const todayWeek =
    document.getElementById(
        "todayWeek"
    );


if (todayWeek) {

    todayWeek.addEventListener(
        "click",
        function() {

            selectedWeekIndex =
                0;


            if (weekFilter) {

                weekFilter.value =
                    0;

            }


            renderCurrentView();

        }
    );

}


/* =========================================================
   QUARTER FILTER
   ========================================================= */

if (quarterFilter) {

    quarterFilter.addEventListener(
        "change",
        function() {

            selectedQuarter =
                quarterFilter.value;


            selectedWeekIndex =
                0;


            selectedDay =
                "Monday";


            clearModuleFilter();


            loadWeeks();


            renderCurrentView();

        }
    );

}


/* =========================================================
   WEEK FILTER
   ========================================================= */

if (weekFilter) {

    weekFilter.addEventListener(
        "change",
        function() {

            selectedWeekIndex =
                parseInt(
                    weekFilter.value,
                    10
                );


            renderCurrentView();

        }
    );

}


/* =========================================================
   CAMPUS FILTER
   ========================================================= */

if (campusFilter) {

    campusFilter.addEventListener(
        "change",
        function() {

            clearModuleFilter();


            renderCurrentView();

        }
    );

}


/* =========================================================
   MODULE SEARCH INPUT
   ========================================================= */

if (moduleSearch) {

    moduleSearch.addEventListener(
        "input",
        function() {

            selectedModule =
                "all";


            showModuleResults();

        }
    );

}


/* =========================================================
   MODULE DROPDOWN
   ========================================================= */

if (moduleDropdown) {

    moduleDropdown.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();


            if (
                moduleResults &&
                moduleResults.style.display ===
                "block"
            ) {

                moduleResults.style.display =
                    "none";

            } else {

                showModuleResults();

                if (moduleSearch) {

                    moduleSearch.focus();

                }

            }

        }
    );

}


/* =========================================================
   CLOSE MODULE DROPDOWN
   ========================================================= */

document.addEventListener(
    "click",
    function(event) {

        if (
            !event.target.closest(
                ".module-select"
            )
        ) {

            if (moduleResults) {

                moduleResults.style.display =
                    "none";

            }

        }

    }
);


/* =========================================================
   RENDER CURRENT VIEW
   ========================================================= */

function renderCurrentView() {

    updateWeekDisplay();


    if (
        currentView === "day"
    ) {

        renderDayView();

    } else {

        renderWeekCalendar();

    }

}


/* =========================================================
   START
   ========================================================= */

loadCampuses();

loadWeeks();

renderCurrentView();