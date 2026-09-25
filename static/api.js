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

async function deleteTeam(teamId) {
    return fetch(`/api/teams/${teamId}`, {method: "DELETE"});
}

async function login(payload) {
    return fetch("/api/auth/login", {
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

async function updateAdminUserRole(userId, role) {
    return fetch(`/api/admin/users/${userId}/role`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({role})
    });
}
