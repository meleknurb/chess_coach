document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector(".search-input");
    const tableBody = document.querySelector(".game-table tbody");

    if (!searchGamesUrl || !analyzeGameUrl) {
        console.error("Django URLs (searchGamesUrl/analyzeGameUrl) are not defined. Check your HTML block.");
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get('query');
    if (initialQuery) {
        searchInput.value = initialQuery;
        performSearch(initialQuery);
    }

    searchInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (!query) return;

            const newUrl = `${window.location.pathname}?query=${encodeURIComponent(query)}`;
            window.history.pushState({path: newUrl}, '', newUrl);

            performSearch(query);
        }
    });

    function performSearch(query) {
        fetch(`${searchGamesUrl}?query=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                tableBody.innerHTML = '';

                if (data.games.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="6" class="no-games">No games found.</td></tr>`;
                    return;
                }

                data.games.forEach(game => {
                    let resultClass;
                    if (game.result_description.includes("Win")) {
                        resultClass = "result-win";
                    } else if (game.result_description.includes("Loss")) {
                        resultClass = "result-loss";
                    } else {
                        resultClass = "result-draw";
                    }

                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${game.date}</td>
                        <td>${game.time_control}</td>
                        <td class="player-details-cell">
                            <div class="player-line white-player">
                                <span class="color-indicator"></span>
                                <span>${game.player_top}</span>
                            </div>
                            <div class="player-line black-player">
                                <span class="color-indicator"></span>
                                <span>${game.player_bottom}</span>
                            </div>
                        </td>
                        <td class="${resultClass}">${game.result_description}</td>
                        <td>${game.moves_count}</td>
                        <td>
                            <form action="${analyzeGameUrl}" method="post">
                                <input type="hidden" name="csrfmiddlewaretoken" value="${getCookie('csrftoken')}">
                                <input type="hidden" name="game_id" value="${game.pk || ''}">
                                <button type="submit" class="btn small-btn analyze-btn">Analyze</button>
                            </form>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            })
            .catch(err => console.error("Search failed:", err));
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                let cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    window.addEventListener('popstate', function(e) {
        const params = new URLSearchParams(window.location.search);
        const query = params.get('query');
        if (query) {
            searchInput.value = query;
            performSearch(query);
        } else {
            searchInput.value = '';
            location.reload(); 
        }
    });
});