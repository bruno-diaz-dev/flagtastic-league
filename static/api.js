// Shared HTTP client functions keep endpoint details out of page controllers.

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value);
    return element.innerHTML;
}

async function getTeams() {
    const response = await fetch("/api/teams");
    return response;
}

async function createTeam(payload) {
    const response = await fetch("/api/teams", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
    return response;
}

async function getTeamDetail(teamId) {
    const response = await fetch(`/api/teams/${teamId}`)
    return response;
}

async function getGames() {
    const response = await fetch("/api/games")
    return response;
}

async function createGame(payload) {
    const response = await fetch("/api/games", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    return response;
}

async function updateGamesScore(gameId, payload) {
    const response = await fetch(`/api/games/${gameId}/score`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    return response;
}

async function getStandings(branch, category) {
    const response = await fetch(
        `/api/standings?branch=${encodeURIComponent(branch)}&category=${encodeURIComponent(category)}`
    );

    return response;
}

async function createPlayer(teamId, payload) {
    const response = await fetch(`/api/teams/${teamId}/players`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    return response
}

async function searchRegisteredPlayers(teamId, query) {
    return fetch(
        `/api/teams/${teamId}/players/candidates?q=${encodeURIComponent(query)}`
    );
}

async function addRegisteredPlayer(teamId, payload) {
    return fetch(`/api/teams/${teamId}/players/registered`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function importRoster(teamId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`/api/teams/${teamId}/players/import`, {
        method: "POST",
        body: formData
    });
}

async function uploadTeamLogo(teamId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`/api/teams/${teamId}/logo`, {
        method: "PUT",
        body: formData
    });
}

async function getGameDetails(gameId) {
    return fetch(`/api/games/${gameId}/details`);
}

async function deleteTeam(teamId) {
    return fetch(`/api/teams/${teamId}`, {method: "DELETE"});
}

function calendarAgeFromCurp(value) {
    const curp = String(value || "").trim().toUpperCase();
    if (curp.length !== 18 || !/^\d{6}$/.test(curp.slice(4, 10))) return null;
    const marker = curp.charAt(16);
    const century = /^\d$/.test(marker) ? 1900 : 2000;
    const year = century + Number(curp.slice(4, 6));
    const month = Number(curp.slice(6, 8));
    const day = Number(curp.slice(8, 10));
    const birthDate = new Date(Date.UTC(year, month - 1, day));
    if (
        birthDate.getUTCFullYear() !== year
        || birthDate.getUTCMonth() !== month - 1
        || birthDate.getUTCDate() !== day
        || birthDate > new Date()
    ) return null;
    return new Date().getFullYear() - year;
}

async function uploadRosterPlayerPhoto(teamId, playerId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`/api/teams/${teamId}/players/${playerId}/photo`, {
        method: "PUT",
        body: formData
    });
}

async function getManagedRosterPlayer(teamId, playerId) {
    return fetch(`/api/teams/${teamId}/players/${playerId}/management`);
}

async function updateRosterPlayer(teamId, playerId, payload) {
    return fetch(`/api/teams/${teamId}/players/${playerId}`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function deactivateRosterPlayer(teamId, playerId) {
    return fetch(`/api/teams/${teamId}/players/${playerId}`, {method: "DELETE"});
}

async function updateTeamStatus(teamId, status) {
    return fetch(`/api/teams/${teamId}/status`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({status})
    });
}

async function updateTeamName(teamId, name) {
    return fetch(`/api/teams/${teamId}/name`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    });
}

async function assignTeamRepresentative(teamId, userId) {
    return fetch(`/api/teams/${teamId}/representatives/${userId}`, {
        method: "PUT"
    });
}

async function getTeamRepresentativeAssignments() {
    return fetch("/api/teams/representative-assignments");
}

async function removeTeamRepresentative(teamId, userId) {
    return fetch(`/api/teams/${teamId}/representatives/${userId}`, {
        method: "DELETE"
    });
}

async function login(payload) {
    return fetch("/api/auth/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function changePassword(payload) {
    return fetch("/api/auth/change-password", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function getLeaderboards(branch, category) {
    return fetch(
        `/api/statistics/leaderboards?branch=${encodeURIComponent(branch)}&category=${encodeURIComponent(category)}`
    );
}

async function importWeekStatistics(week, file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`/api/weeks/${week}/player-stats/import`, {
        method: "POST",
        body: formData
    });
}

async function importOfficialStatistics(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch("/api/statistics/import", {
        method: "POST",
        body: formData
    });
}

async function registerPlayerAccount(payload) {
    return fetch("/api/auth/register/player", {
        method: "POST",
        // The browser supplies the multipart boundary for profile photo uploads.
        body: payload
    });
}

async function getMyDashboard() {
    return fetch("/api/me/dashboard");
}

async function joinMyTeam(teamId, payload) {
    return fetch(`/api/me/teams/${teamId}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function getAdminUsers() {
    return fetch("/api/admin/users");
}

async function createStaffAccount(payload) {
    return fetch("/api/admin/users", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function updateAdminUserRole(userId, role) {
    return fetch(`/api/admin/users/${userId}/role`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({role})
    });
}

async function updateAdminUserRoles(userId, roles) {
    return fetch(`/api/admin/users/${userId}/roles`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({roles})
    });
}

async function updateTeamStaff(teamId, payload) {
    return fetch(`/api/teams/${teamId}/staff`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function getMyRepresentativeDashboard() {
    return fetch("/api/me/representative-dashboard");
}

async function deleteAdminUser(userId) {
    return fetch(`/api/admin/users/${userId}`, {method: "DELETE"});
}

async function getPublicPlayerProfile(playerId) {
    return fetch(`/api/players/${playerId}/profile`);
}

async function getMyRefereeGames() {
    return fetch("/api/games/mine/referee");
}

async function getGameReferees(gameId) {
    return fetch(`/api/games/${gameId}/referees`);
}

async function assignGameReferee(gameId, userId, position) {
    return fetch(`/api/games/${gameId}/referees/${userId}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({position})
    });
}

async function updateMyProfile(payload) {
    return fetch("/api/me/profile", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
}

async function removeGameReferee(gameId, userId) {
    return fetch(`/api/games/${gameId}/referees/${userId}`, {method: "DELETE"});
}

async function analyzeRefereeSchedule(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch("/api/games/referee-schedule/analyze", {
        method: "POST",
        body: formData
    });
}

async function confirmRefereeSchedule(assignments) {
    return fetch("/api/games/referee-schedule/confirm", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({assignments})
    });
}

async function analyzeGameSchedule(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetch("/api/games/schedule/analyze", {
        method: "POST",
        body: formData
    });
}

async function confirmGameSchedule(games) {
    return fetch("/api/games/schedule/confirm", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({games})
    });
}
