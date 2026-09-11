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